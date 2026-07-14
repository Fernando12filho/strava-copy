function initImportFlow(uploadUrl) {
  const idleEl = document.getElementById("import-idle");
  const processingEl = document.getElementById("import-processing");
  const doneEl = document.getElementById("import-done");
  const errorEl = document.getElementById("import-error");
  const fileInput = document.getElementById("import-file-input");
  const chooseBtn = document.getElementById("choose-file-btn");
  const anotherBtn = document.getElementById("import-another-btn");

  const progressFill = document.getElementById("progress-fill");
  const progressPct = document.getElementById("progress-pct");
  const progressRecords = document.getElementById("progress-records");
  const processingStage = document.getElementById("processing-stage");
  const processingFilename = document.getElementById("processing-filename");

  const STAGES = [
    [0, "Unzipping archive"],
    [12, "Reading export.xml"],
    [34, "Parsing workout records"],
    [61, "Matching GPS routes"],
    [83, "De-duplicating against database"],
    [96, "Building indexes"],
  ];
  const stageLabel = (pct) => {
    let label = STAGES[0][1];
    for (const [threshold, text] of STAGES) {
      if (pct >= threshold) label = text;
    }
    return label;
  };

  let progressTimer = null;
  let pct = 0;

  function showState(el) {
    [idleEl, processingEl, doneEl].forEach((node) => {
      node.style.display = node === el ? "" : "none";
    });
    errorEl.style.display = "none";
  }

  function setProgress(value) {
    pct = value;
    progressFill.style.width = pct + "%";
    progressPct.textContent = Math.round(pct) + "%";
    processingStage.textContent = stageLabel(pct);
  }

  function resetToIdle() {
    clearInterval(progressTimer);
    fileInput.value = "";
    setProgress(0);
    showState(idleEl);
  }

  function formatBytes(bytes) {
    return (bytes / (1024 * 1024)).toFixed(0) + " MB";
  }

  async function startImport(file) {
    processingFilename.textContent = file.name;
    showState(processingEl);
    setProgress(0);

    progressTimer = setInterval(() => {
      setProgress(Math.min(90, pct + Math.max(0.5, (90 - pct) * 0.06)));
    }, 130);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(uploadUrl, { method: "POST", body: formData });
      const data = await response.json();
      clearInterval(progressTimer);

      if (!response.ok) {
        showState(idleEl);
        errorEl.textContent = "Error: " + (data.error || "import failed");
        errorEl.style.display = "";
        return;
      }

      setProgress(100);
      document.getElementById("done-meta").textContent =
        file.name + " · " + formatBytes(data.size_bytes) + " · " + data.elapsed_seconds + "s";
      document.getElementById("done-imported").textContent = data.imported.toLocaleString();
      document.getElementById("done-skipped").textContent = data.skipped.toLocaleString();
      document.getElementById("done-range").textContent = data.date_range || "—";
      showState(doneEl);
    } catch (err) {
      clearInterval(progressTimer);
      showState(idleEl);
      errorEl.textContent = "Error: could not reach the local server.";
      errorEl.style.display = "";
    }
  }

  chooseBtn.addEventListener("click", () => fileInput.click());
  idleEl.addEventListener("click", (e) => {
    if (e.target === chooseBtn) return;
    fileInput.click();
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) startImport(fileInput.files[0]);
  });

  ["dragenter", "dragover"].forEach((evt) =>
    idleEl.addEventListener(evt, (e) => {
      e.preventDefault();
      idleEl.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    idleEl.addEventListener(evt, (e) => {
      e.preventDefault();
      idleEl.classList.remove("dragover");
    })
  );
  idleEl.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) startImport(file);
  });

  anotherBtn.addEventListener("click", resetToIdle);
}
