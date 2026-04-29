from .favicon import FAVICON_FILENAME


def build_header_icon() -> str:
    return """
<svg width="18" height="18" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect width="64" height="64" rx="10" fill="#3a3a3a"/>
  <rect x="14" y="14" width="34" height="4" fill="#4aa3ff"/>
  <rect x="20" y="22" width="30" height="4" fill="#2ecc71"/>
  <rect x="20" y="30" width="34" height="4" fill="#4aa3ff"/>
  <rect x="14" y="38" width="40" height="5" fill="#e74c3c"/>
  <rect x="14" y="48" width="28" height="4" fill="#4aa3ff"/>
</svg>
"""


def build_report_shell(styles: str, script: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <link rel="icon" href="{FAVICON_FILENAME}" type="image/x-icon">
  <link rel="shortcut icon" href="{FAVICON_FILENAME}" type="image/x-icon">
  <title>AstAnalyzer – Scan Results</title>
  {styles}
</head>
<body>
  <header>
    <h1 class="app-title">
      {build_header_icon()}
      <span id="reportTitleText">AstAnalyzer – Scan Results</span>
    </h1>

    <div class="row">
      <span class="pill" id="status">Loaded</span>
      <span class="pill" id="counts">0 findings / 0 fixes selected / 0 actions selected</span>
      <span class="pill" id="sourceHint">scan_report.json</span>
      <span class="pill" id="saveTarget">Target: download fallback</span>
      <span class="pill" id="viewStatus">View: Rule first</span>
    </div>
  </header>

  <main>
    <div class="toolbar toolbar-main">
        <input id="fileInput" type="file" accept=".json,application/json" />
    </div>
    <div class="toolbar toolbar-main">
        <p>Selection:</p>
        <button id="btnSelectAll">Select all findings</button>
        <button id="btnClear">Clear selection</button>
    </div>
    <div class="toolbar toolbar-selection">
        <p>Export:</p>
        <button id="btnPickDir">Choose folder</button>
        <button id="btnExport">Export selected.json</button>
    </div>

    <div class="toolbar toolbar-view">
        <input id="search" type="search" placeholder="Filter: file, rule_id, title, text..." />

        <div class="view-toggle">
            <button id="btnRuleFirst" type="button">Rule first</button>
            <button id="btnFileFirst" type="button">File first</button>
        </div>
    </div>
    
    <div class="hint">
      Open report → Review findings → select fixes → export selected.json → run astanalyzer patch
    </div>

    <div id="hint" class="warn" style="display:none; margin: 0 0 12px;"></div>
    <div class="grid" id="list"></div>
  </main>

  <footer>
    This page was generated from AstAnalyzer scan_report.json.
  </footer>

  {script}
</body>
</html>"""
