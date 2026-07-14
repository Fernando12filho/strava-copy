function _coalesce(times, values) {
  const t = [];
  const v = [];
  for (let i = 0; i < times.length; i++) {
    if (values[i] !== null && values[i] !== undefined) {
      t.push(times[i]);
      v.push(values[i]);
    }
  }
  return [t, v];
}

function _interpolate(xs, ys, targetX) {
  if (targetX <= xs[0]) return ys[0];
  if (targetX >= xs[xs.length - 1]) return ys[ys.length - 1];
  for (let i = 1; i < xs.length; i++) {
    if (xs[i] >= targetX) {
      const x0 = xs[i - 1];
      const x1 = xs[i];
      const y0 = ys[i - 1];
      const y1 = ys[i];
      if (x1 === x0) return y1;
      return y0 + ((targetX - x0) / (x1 - x0)) * (y1 - y0);
    }
  }
  return ys[ys.length - 1];
}

function _nearest(times, values, targetTime) {
  if (!times.length) return null;
  let best = 0;
  let bestDiff = Infinity;
  for (let i = 0; i < times.length; i++) {
    const diff = Math.abs(times[i] - targetTime);
    if (diff < bestDiff) {
      bestDiff = diff;
      best = i;
    }
  }
  return values[best];
}

function _fmtClock(v) {
  if (v === null || v === undefined || !isFinite(v)) return "";
  const m = Math.floor(v);
  const s = Math.round((v - m) * 60);
  return m + ":" + String(s).padStart(2, "0");
}

async function initActivityCharts(streamUrl) {
  const response = await fetch(streamUrl);
  const stream = await response.json();

  const [distTimes, dists] = _coalesce(stream.time, stream.distance);
  if (distTimes.length < 2) return;

  const [hrTimes, hrs] = _coalesce(stream.time, stream.hr);
  const [elevTimes, elevs] = _coalesce(stream.time, stream.elevation);

  const bucketCount = Math.max(1, Math.min(60, distTimes.length - 1));
  const bucketTimes = [];
  const bucketDistKm = [];
  for (let i = 0; i <= bucketCount; i++) {
    const targetDist = dists[0] + (i / bucketCount) * (dists[dists.length - 1] - dists[0]);
    bucketTimes.push(_interpolate(dists, distTimes, targetDist));
    bucketDistKm.push(targetDist / 1000);
  }

  const paceLabels = bucketDistKm.slice(1);
  const paceSeries = [];
  for (let i = 1; i <= bucketCount; i++) {
    const dt = bucketTimes[i] - bucketTimes[i - 1];
    const dd = bucketDistKm[i] - bucketDistKm[i - 1];
    paceSeries.push(dd > 0 ? dt / 60 / dd : null);
  }

  const hrSeries = bucketTimes.map((t) => _nearest(hrTimes, hrs, t));
  const elevSeries = bucketTimes.map((t) => _nearest(elevTimes, elevs, t));

  const baseX = (labels, showTicks) => ({
    grid: { display: false },
    border: { color: "#26262E", display: showTicks },
    ticks: {
      display: showTicks,
      color: "#5E5E68",
      font: { family: "'JetBrains Mono'", size: 9 },
      maxTicksLimit: 8,
      callback: (v, i) => labels[i].toFixed(1) + (i === labels.length - 1 ? " km" : ""),
    },
  });

  const common = (bodyColor) => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#1E1E26",
        borderColor: "#2C2C36",
        borderWidth: 1,
        titleColor: "#5E5E68",
        bodyColor,
        bodyFont: { family: "'JetBrains Mono'" },
        titleFont: { family: "'JetBrains Mono'", size: 10 },
        displayColors: false,
        padding: 8,
      },
    },
    elements: { point: { radius: 0 } },
  });

  const render = (id, labels, data, color, fill, showXTicks, yFmt) => {
    const el = document.getElementById(id);
    if (!el) return;
    new Chart(el.getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            data,
            borderColor: color,
            borderWidth: 2,
            tension: 0.35,
            spanGaps: true,
            fill: fill ? { target: "origin" } : false,
            backgroundColor: fill ? "rgba(60,60,72,0.35)" : "transparent",
          },
        ],
      },
      options: {
        ...common(color),
        scales: {
          x: baseX(labels, showXTicks),
          y: {
            grid: { color: "#17171D" },
            border: { display: false },
            ticks: { color: "#5E5E68", font: { family: "'JetBrains Mono'", size: 9 }, maxTicksLimit: 3, callback: yFmt },
          },
        },
      },
    });
  };

  render("paceChart", paceLabels, paceSeries, "#C4F82A", false, false, _fmtClock);
  render("hrChart", bucketDistKm, hrSeries, "#C4F82A", false, false, (v) => Math.round(v));
  render("elevChart", bucketDistKm, elevSeries, "#6C6C78", true, true, (v) => Math.round(v));
}
