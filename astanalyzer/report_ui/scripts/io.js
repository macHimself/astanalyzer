function setHint(msg, cls = "warn") {
  const elHint = document.getElementById("hint");
  if (!msg) {
    elHint.style.display = "none";
    elHint.textContent = "";
    elHint.className = "";
    return;
  }
  elHint.style.display = "block";
  elHint.textContent = msg;
  elHint.className = cls;
}

function hasDirectoryPickerSupport() {
  return typeof window.showDirectoryPicker === "function";
}

function updateSaveTargetLabel() {
  if (state.dirHandle && state.dirHandle.name) {
    elSaveTarget.textContent = `Target: ${state.dirHandle.name}`;
  } else {
    elSaveTarget.textContent = "Target: download fallback";
  }
}

function updateViewButtons() {
  btnRuleFirst.classList.toggle("active", state.viewMode === "rule-first");
  btnFileFirst.classList.toggle("active", state.viewMode === "file-first");
  elViewStatus.textContent =
    state.viewMode === "rule-first" ? "View: Rule first" : "View: File first";
}

function updateCounts() {
  elCounts.textContent =
    `${state.findings.length} findings / ` +
    `${state.selected.size} fixes selected / ` +
    `${state.selectedActions.size} actions selected`;
}

function enableButtons(enabled) {
  btnSelectAll.disabled = !enabled;
  btnClear.disabled = !enabled;
  btnExport.disabled = !enabled;
}

function matchesFilter(finding) {
  const q = state.filter.trim().toLowerCase();
  if (!q) return true;

  const hay = [
    finding.id,
    finding.rule_id,
    finding.category,
    finding.title,
    finding.severity,
    finding.file,
    finding.message,
    ...finding.fixes.map(fx => fx.title),
    ...finding.fixes.map(fx => fx.reason),
    "Suppress this warning"
  ].join(" ").toLowerCase();

  return hay.includes(q);
}

function loadFromFile(file) {
  setHint("");
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const json = JSON.parse(reader.result);
      applyJson(json, `file: ${file.name}`);
    } catch (e) {
      setHint("Invalid JSON.");
      console.error(e);
    }
  };
  reader.readAsText(file);
}

async function pickDirectory() {
  setHint("");

  if (!hasDirectoryPickerSupport()) {
    setHint(
        "Folder selection not supported. Using standard download.",
        "info");
        return;
  }

  try {
    const handle = await window.showDirectoryPicker();
    state.dirHandle = handle;
    updateSaveTargetLabel();
    setHint(`Selected folder: ${handle.name}`, "ok");
  } catch (err) {
    if (err && err.name !== "AbortError") {
      console.error(err);
      setHint("Could not select folder.");
    }
  }
}

async function saveBlobToPickedDirectory(filename, blob) {
  if (!state.dirHandle) {
    throw new Error("No directory selected.");
  }

  const fileHandle = await state.dirHandle.getFileHandle(filename, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(blob);
  await writable.close();
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function exportSelected() {
  const grouped = {};
  const selectedActions = [];

  for (const [, v] of state.selected.entries()) {
    const f = v.finding;
    const fx = v.fix;
    const key = f.id;

    if (!grouped[key]) {
      grouped[key] = {
        id: f.id,
        rule_id: f.rule_id,
        title: f.title,
        severity: f.severity,
        file: f.file,
        start_line: f.start_line,
        end_line: f.end_line,
        message: f.message,
        anchor: f.anchor ?? null,
        selected_fixes: []
      };
    }

    grouped[key].selected_fixes.push({
      fix_id: fx.fix_id,
      fixer_index: fx.fixer_index,
      title: fx.title,
      reason: fx.reason,
      dsl: fx.dsl
    });
  }

  for (const [, v] of state.selectedActions.entries()) {
    const f = v.finding;
    selectedActions.push({
      type: "ignore_finding",
      finding_id: f.id,
      rule_id: f.rule_id,
      title: f.title,
      severity: f.severity,
      file: f.file,
      start_line: f.start_line,
      end_line: f.end_line,
      message: f.message,
      anchor: f.anchor ?? null
    });
  }

  const out = {
    generated_at: new Date().toISOString(),
    project_root: state.raw?.project_root ?? null,
    selected_fix_count: state.selected.size,
    selected_action_count: state.selectedActions.size,
    findings: Object.values(grouped),
    selected_actions: selectedActions
  };

  const filename = "astanalyzer-selected.json";
  const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });

  try {
    if (state.dirHandle && hasDirectoryPickerSupport()) {
      await saveBlobToPickedDirectory(filename, blob);
      setHint(`The file was saved to the selected folder as ${filename}.`, "ok");
      return;
    }

    downloadBlob(filename, blob);
    setHint("The browser used the standard file download.");
  } catch (err) {
    console.error(err);
    setHint("Direct save to folder failed. The file will be downloaded normally.");
    downloadBlob(filename, blob);
  }
}