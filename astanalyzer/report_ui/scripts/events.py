def build_script_events() -> str:
    return """
fileInput.addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (file) loadFromFile(file);
});

search.addEventListener("input", (e) => {
  state.filter = e.target.value;
  render();
});

btnPickDir.addEventListener("click", () => {
  pickDirectory();
});

btnRuleFirst.addEventListener("click", () => {
  state.viewMode = "rule-first";
  render();
});

btnFileFirst.addEventListener("click", () => {
  state.viewMode = "file-first";
  render();
});

btnSelectAll.addEventListener("click", () => {
  state.findings.filter(matchesFilter).forEach((f) => {
    const firstFix = f.fixes[0];
    if (firstFix) {
      removeSelectedFixesForFinding(f);
      state.selected.set(fixKey(f, firstFix), { finding: f, fix: firstFix });
    }
  });
  updateCounts();
  rerenderKeepingOpenDetails();
});

btnClear.addEventListener("click", () => {
  state.selected.clear();
  state.selectedActions.clear();
  updateCounts();
  rerenderKeepingOpenDetails();
});

btnExport.addEventListener("click", () => {
  exportSelected();
});

updateSaveTargetLabel();
updateViewButtons();
applyJson(state.raw, "scan_report.json");
"""