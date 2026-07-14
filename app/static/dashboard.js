function initWeeklyVolumeChart(canvasId, labels, data) {
  const el = document.getElementById(canvasId);
  if (!el) return;

  new Chart(el.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data,
          backgroundColor: "#C4F82A",
          hoverBackgroundColor: "#d6ff5c",
          borderRadius: 4,
          barPercentage: 0.62,
          categoryPercentage: 0.8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1E1E26",
          borderColor: "#2C2C36",
          borderWidth: 1,
          titleColor: "#ECECEF",
          bodyColor: "#C4F82A",
          bodyFont: { family: "'JetBrains Mono'" },
          titleFont: { family: "'JetBrains Mono'" },
          padding: 10,
          displayColors: false,
          callbacks: { label: (c) => c.parsed.y + " km" },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { color: "#26262E" },
          ticks: { color: "#5E5E68", font: { family: "'JetBrains Mono'", size: 10 } },
        },
        y: {
          beginAtZero: true,
          grid: { color: "#1A1A20" },
          border: { display: false },
          ticks: { color: "#5E5E68", font: { family: "'JetBrains Mono'", size: 10 } },
        },
      },
    },
  });
}
