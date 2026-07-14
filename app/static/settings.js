function initSettingsForm(postUrl) {
  const form = document.getElementById("settings-form");
  const saveStatus = document.getElementById("save-status");
  const maxHrInput = document.getElementById("max-hr-input");
  const zoneChips = document.querySelectorAll("#hr-zones-list .hr-zone-chip");
  const unitsInput = document.getElementById("units-input");
  const unitsButtons = document.querySelectorAll("#units-segmented .segmented-btn");
  const wipeForm = document.getElementById("wipe-form");

  let saveTimer = null;

  function markDirty() {
    saveStatus.textContent = "Unsaved changes · auto-saved locally";
    saveStatus.classList.add("dirty");
    clearTimeout(saveTimer);
    saveTimer = setTimeout(autosave, 700);
  }

  function markSaved() {
    saveStatus.textContent = "All changes saved";
    saveStatus.classList.remove("dirty");
  }

  async function autosave() {
    const formData = new FormData(form);
    try {
      await fetch(postUrl, { method: "POST", body: formData, headers: { "X-Requested-With": "fetch" } });
      markSaved();
    } catch (err) {
      /* keep dirty status; next edit will retry */
    }
  }

  function recomputeZones() {
    const fallback = parseInt(maxHrInput.placeholder, 10) || 190;
    const maxHr = parseInt(maxHrInput.value, 10) || fallback;
    zoneChips.forEach((chip) => {
      const lo = parseFloat(chip.dataset.lo);
      const hi = parseFloat(chip.dataset.hi);
      chip.querySelector(".hr-zone-bpm").textContent = Math.round(lo * maxHr) + "–" + Math.round(hi * maxHr) + " bpm";
    });
  }

  form.addEventListener("input", () => {
    recomputeZones();
    markDirty();
  });

  unitsButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      unitsButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      unitsInput.value = btn.dataset.units;
      markDirty();
    });
  });

  if (wipeForm) {
    wipeForm.addEventListener("submit", (e) => {
      if (!confirm("Permanently delete all imported activities? This cannot be undone.")) {
        e.preventDefault();
      }
    });
  }
}
