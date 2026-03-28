"""
HTML report UI generation for astanalyzer.

This module builds a standalone HTML page for browsing findings from
`scan_report.json`, selecting fix proposals, and exporting the selected
subset into a JSON file for later patch generation.
"""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path


def build_report_html(report_data: dict) -> str:
    """Build a standalone HTML report page from scan JSON data."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>astanalyzer – Fix Plan Picker</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      margin: 0;
    }}
    header {{
      padding: 16px 20px;
      border-bottom: 1px solid rgba(127,127,127,.25);
      position: sticky;
      top: 0;
      background: Canvas;
      z-index: 10;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 18px;
    }}
    .row {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .pill {{
      padding: 6px 10px;
      border: 1px solid rgba(127,127,127,.35);
      border-radius: 999px;
      font-size: 12px;
    }}
    main {{
      padding: 16px 20px;
      max-width: 1100px;
      margin: 0 auto;
    }}
    .toolbar {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 12px 0 18px;
      align-items: center;
    }}
    button, input[type="file"] {{
      border: 1px solid rgba(127,127,127,.35);
      background: transparent;
      padding: 8px 12px;
      border-radius: 10px;
      cursor: pointer;
      font: inherit;
    }}
    button:disabled {{
      opacity: .5;
      cursor: not-allowed;
    }}
    input[type="search"] {{
      border: 1px solid rgba(127,127,127,.35);
      padding: 8px 12px;
      border-radius: 10px;
      min-width: 280px;
      font: inherit;
      background: transparent;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
    }}
    .card {{
      border: 1px solid rgba(127,127,127,.25);
      border-radius: 14px;
      padding: 12px 14px;
      background: color-mix(in oklab, Canvas, CanvasText 2%);
    }}
    .topline {{
      display: flex;
      gap: 12px;
      justify-content: space-between;
      align-items: baseline;
      flex-wrap: wrap;
    }}
    .title {{
      font-weight: 700;
    }}
    .meta {{
      opacity: .75;
      font-size: 12px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .path {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
    }}
    .desc {{
      margin: 10px 0 0;
      padding: 10px 12px;
      border-left: 4px solid rgba(127,127,127,.45);
      border-radius: 10px;
      background: color-mix(in oklab, Canvas, CanvasText 4%);
      line-height: 1.45;
      white-space: pre-wrap;
    }}
    .fixes {{
      margin-top: 10px;
      display: grid;
      gap: 8px;
    }}
    .fix {{
      border: 1px dashed rgba(127,127,127,.35);
      border-radius: 12px;
      padding: 10px 10px;
      display: grid;
      gap: 6px;
    }}
    .fix label {{
      display: flex;
      gap: 10px;
      align-items: flex-start;
    }}
    .fix .fix-title {{
      font-weight: 600;
    }}
    .fix .fix-reason {{
      opacity: .85;
      font-size: 12px;
    }}
    .code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      padding: 10px;
      border-radius: 10px;
      border: 1px solid rgba(127,127,127,.25);
      overflow: auto;
      background: color-mix(in oklab, Canvas, CanvasText 5%);
      white-space: pre;
    }}
    footer {{
      padding: 18px 20px;
      opacity: .75;
      font-size: 12px;
      text-align: center;
    }}
    .warn {{
      color: #b45309;
    }}
    .ok {{
      color: #166534;
    }}
  </style>
</head>
<body>
  <header>
    <h1>astanalyzer – fix selection from JSON plan</h1>
    <div class="row">
      <span class="pill" id="status">Loaded</span>
      <span class="pill" id="counts">0 findings / 0 fixes selected</span>
      <span class="pill" id="sourceHint">scan_report.json</span>
      <span class="pill" id="saveTarget">Target: download fallback</span>
    </div>
  </header>

  <main>
    <div class="toolbar">
      <input id="fileInput" type="file" accept="application/json,.json" />
      <input id="search" type="search" placeholder="Filter: file, rule_id, title, text…" />
      <button id="btnPickDir">Choose folder</button>
      <button id="btnSelectAll" disabled>Select all</button>
      <button id="btnClear" disabled>Clear selection</button>
      <button id="btnExport" disabled>Export selected.json</button>
    </div>

    <div id="hint" class="warn" style="display:none; margin: 0 0 12px;"></div>
    <div class="grid" id="list"></div>
  </main>

  <footer>
    This page was generated from scan_report.json.
  </footer>

<script>
const state = {{
  raw: {json.dumps(report_data, ensure_ascii=False, indent=2)},
  findings: [],
  selected: new Map(),
  filter: "",
  dirHandle: null
}};

const elStatus = document.getElementById("status");
const elCounts = document.getElementById("counts");
const elList = document.getElementById("list");
const elHint = document.getElementById("hint");
const elSourceHint = document.getElementById("sourceHint");
const elSaveTarget = document.getElementById("saveTarget");

const fileInput = document.getElementById("fileInput");
const search = document.getElementById("search");
const btnPickDir = document.getElementById("btnPickDir");
const btnSelectAll = document.getElementById("btnSelectAll");
const btnClear = document.getElementById("btnClear");
const btnExport = document.getElementById("btnExport");

function setHint(msg, cls = "warn") {{
  if (!msg) {{
    elHint.style.display = "none";
    elHint.textContent = "";
    elHint.className = "warn";
    return;
  }}
  elHint.style.display = "block";
  elHint.textContent = msg;
  elHint.className = cls;
}}

function hasDirectoryPickerSupport() {{
  return typeof window.showDirectoryPicker === "function";
}}

function updateSaveTargetLabel() {{
  if (state.dirHandle && state.dirHandle.name) {{
    elSaveTarget.textContent = `Target: ${{state.dirHandle.name}}`;
  }} else {{
    elSaveTarget.textContent = "Target: download fallback";
  }}
}}

function normalisePlan(json) {{
  const findings = Array.isArray(json)
    ? json
    : (json.findings ?? json.results ?? json.items ?? []);

  if (!Array.isArray(findings)) return [];

  return findings.map((f, idx) => {{
    const fixes = f.fixes ?? f.fix_proposals ?? f.proposals ?? f.selected_fixes ?? [];
    return {{
      _idx: idx,
      id: f.id ?? f.finding_id ?? f.match_id ?? `${{idx}}`,
      rule_id: f.rule_id ?? f.rule ?? f.code ?? "UNKNOWN_RULE",
      title: f.title ?? f.headline ?? f.name ?? "Untitled finding",
      severity: f.severity ?? f.level ?? "info",
      file: f.file ?? f.filename ?? f.path ?? "unknown",
      start_line: f.start_line ?? f.lineno ?? f.line ?? null,
      end_line: f.end_line ?? f.end_lineno ?? null,
      message: f.message ?? f.description ?? f.desc ?? f.details ?? f.text ?? "",
      anchor: f.anchor ?? null,
      raw_finding: f,
      fixes: Array.isArray(fixes) ? fixes.map((x, j) => ({{
        _jdx: j,
        fix_id: x.fix_id ?? x.id ?? `${{idx}}:${{j}}`,
        fixer_index: x.fixer_index ?? x.index ?? j,
        title: x.title ?? x.name ?? "Fix",
        reason: x.reason ?? x.because ?? x.note ?? "",
        dsl: x.dsl ?? x.plan ?? x.actions ?? x,
        patch_preview: x.patch_preview ?? x.patch ?? x.preview ?? "",
        raw_fix: x
      }})) : []
    }};
  }});
}}

function fixKey(finding, fix) {{
  return `${{finding.file}}::${{finding.id}}::${{fix.fix_id}}`;
}}

function updateCounts() {{
  elCounts.textContent = `${{state.findings.length}} findings / ${{state.selected.size}} fixes selected`;
}}

function enableButtons(enabled) {{
  btnSelectAll.disabled = !enabled;
  btnClear.disabled = !enabled;
  btnExport.disabled = !enabled;
}}

function matchesFilter(finding) {{
  const q = state.filter.trim().toLowerCase();
  if (!q) return true;

  const hay = [
    finding.id,
    finding.rule_id,
    finding.title,
    finding.severity,
    finding.file,
    finding.message,
    ...finding.fixes.map(fx => fx.title),
    ...finding.fixes.map(fx => fx.reason)
  ].join(" ").toLowerCase();

  return hay.includes(q);
}}

function formatLines(s, e) {{
  if (!s && !e) return "";
  if (s && e && s !== e) return `:${{s}}-${{e}}`;
  return `:${{s ?? e}}`;
}}

function escapeHtml(str) {{
  return String(str).replace(/[&<>"']/g, s => ({{
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }}[s]));
}}

function normaliseDslObject(dsl) {{
  if (!dsl) return null;

  if (typeof dsl === "string") {{
    try {{
      return JSON.parse(dsl);
    }} catch {{
      return {{ raw: dsl }};
    }}
  }}

  if (Array.isArray(dsl)) {{
    return {{ actions: dsl }};
  }}

  if (typeof dsl === "object") {{
    return dsl;
  }}

  return {{ raw: String(dsl) }};
}}

function describeAction(action) {{
  const op = action?.op ?? "unknown_op";
  const text = action?.text ?? "";
  const ref = action?.ref ?? action?.target_ref ?? "";
  const label = action?.label ?? action?.title ?? action?.summary ?? action?.description ?? "";
  const note = action?.comment ?? action?.reason ?? "";

  switch (op) {{
    case "comment_on_function":
      return text ? "Add a comment to the function: " + text : "Add a comment to the function.";

    case "insert_at_body_start":
      return text ? "Insert at the start of the block body: " + text : "Insert content at the start of the block body.";

    case "add_docstring":
      return text ? "Add a docstring: " + text : "Add a docstring.";

    case "delete_node":
      return "Remove the entire problematic node from the code.";

    case "remove_node":
      return ref ? 'Remove the node marked as "' + ref + '".' : "Remove the selected node.";

    case "append_line":
      return text ? "Add a new line: " + text : "Add a new line.";

    case "prepend_line":
      return text ? "Insert a new line before the existing code: " + text : "Insert a new line before the existing code.";

    case "replace_text":
      return "Replace part of the text with new content.";

    case "remove_line":
      return "Remove the line.";

    case "insert_comment":
      if (text) return "Insert a comment before the node: " + text;
      if (label) return label;
      if (note) return note;
      return "Insert a generated comment before the node.";

    case "insert_before":
      return text ? "Insert before the node: " + text : "Insert content before the node.";

    case "insert_after":
      return text ? "Insert after the node: " + text : "Insert content after the node.";

    case "remove_dead_code_after_return":
      return "Remove dead code after return.";

    case "replace_node":
      return "Replace the entire node with new content.";

    case "custom":
      if (label) return label;
      if (text) return text;
      if (note) return note;
      return "Perform a custom refactoring step.";

    default:
      return 'Perform operation "' + op + '".';
  }}
}}

function buildHumanFixText(fx) {{
  const dslObj = normaliseDslObject(fx.dsl);
  if (!dslObj) return "";

  const lines = [];
  const why = fx.reason || dslObj.because || "";

  const actions = Array.isArray(dslObj.actions) ? dslObj.actions : [];
  if (actions.length) {{
    //lines.push("Proposed steps:");
    actions.forEach((action, i) => {{
      let step = describeAction(action);
      const extraNote = action?.comment ?? action?.reason ?? "";
      if (extraNote) {{
        step += " Note: " + extraNote;
      }}
      lines.push(step);
    }});
  }}

  return lines.join("\\n");
}}

function render() {{
  elList.innerHTML = "";
  const visible = state.findings.filter(matchesFilter);

  visible.forEach(f => {{
    const card = document.createElement("div");
    card.className = "card";

    const topline = document.createElement("div");
    topline.className = "topline";

    const left = document.createElement("div");
    left.innerHTML = `
      <div class="title">${{escapeHtml(f.title)}}</div>
      <div class="meta">
        <span class="pill">${{escapeHtml(f.severity)}}</span>
        <span class="pill">${{escapeHtml(f.rule_id)}}</span>
        <span class="pill">${{escapeHtml(f.id)}}</span>
        <span class="pill path">${{escapeHtml(f.file)}}${{formatLines(f.start_line, f.end_line)}}</span>
      </div>
    `;
    topline.appendChild(left);
    card.appendChild(topline);

    if (f.message) {{
      const desc = document.createElement("div");
      desc.className = "desc";
      desc.innerHTML = `<strong>Message:</strong> ${{escapeHtml(f.message)}}`;
      card.appendChild(desc);
    }}

    const fixesWrap = document.createElement("div");
    fixesWrap.className = "fixes";

    if (!f.fixes.length) {{
      const none = document.createElement("div");
      none.className = "fix";
      none.textContent = "No fix proposals in this finding.";
      fixesWrap.appendChild(none);
    }} else {{
      f.fixes.forEach(fx => {{
        const k = fixKey(f, fx);
        const fixDiv = document.createElement("div");
        fixDiv.className = "fix";

        const checked = state.selected.has(k);

        const label = document.createElement("label");
        label.innerHTML = `
          <input type="checkbox" ${{checked ? "checked" : ""}} />
          <div>
            <div class="fix-title">${{escapeHtml(fx.title)}}</div>
            ${{fx.reason
              ? `<div class="fix-reason">${{escapeHtml(fx.reason)}}</div>`
              : `<div class="fix-reason">reason: &lt;missing&gt;</div>`}}
          </div>
        `;

        const cb = label.querySelector("input");
        cb.addEventListener("change", (e) => {{
          if (e.target.checked) {{
            state.selected.set(k, {{ finding: f, fix: fx }});
          }} else {{
            state.selected.delete(k);
          }}
          updateCounts();
        }});

        fixDiv.appendChild(label);

        const humanText = buildHumanFixText(fx);
        if (humanText) {{
          const desc = document.createElement("div");
          desc.className = "desc";
          desc.innerHTML = `${{escapeHtml(humanText)}}`;//<strong>Proposed solution:</strong>
          fixDiv.appendChild(desc);
        }}

        const dslText = typeof fx.dsl === "string"
          ? fx.dsl
          : JSON.stringify(fx.dsl, null, 2);

        if (dslText && dslText !== "{{}}" && dslText !== "[]") {{
          const details = document.createElement("details");
          const summary = document.createElement("summary");
          summary.textContent = "Raw detail";

          const pre = document.createElement("div");
          pre.className = "code";
          pre.textContent = dslText;

          details.appendChild(summary);
          details.appendChild(pre);
          //fixDiv.appendChild(details);
        }}

        fixesWrap.appendChild(fixDiv);
      }});
    }}

    card.appendChild(fixesWrap);
    elList.appendChild(card);
  }});

  elStatus.textContent = state.raw ? "Loaded" : "No data";
  updateCounts();
}}

function applyJson(json, source) {{
  state.raw = json;
  state.findings = normalisePlan(json);
  state.selected.clear();
  elSourceHint.textContent = source ?? "JSON";
  enableButtons(true);
  render();
}}

function loadFromFile(file) {{
  setHint("");
  const reader = new FileReader();
  reader.onload = () => {{
    try {{
      const json = JSON.parse(reader.result);
      applyJson(json, `file: ${{file.name}}`);
    }} catch (e) {{
      setHint("Invalid JSON.");
      console.error(e);
    }}
  }};
  reader.readAsText(file);
}}

async function pickDirectory() {{
  setHint("");

  if (!hasDirectoryPickerSupport()) {{
    setHint("This browser does not support folder selection. Standard file download will be used.");
    return;
  }}

  try {{
    const handle = await window.showDirectoryPicker();
    state.dirHandle = handle;
    updateSaveTargetLabel();
    setHint(`Selected folder: ${{handle.name}}`, "ok");
  }} catch (err) {{
    if (err && err.name !== "AbortError") {{
      console.error(err);
      setHint("Could not select folder.");
    }}
  }}
}}

async function saveBlobToPickedDirectory(filename, blob) {{
  if (!state.dirHandle) {{
    throw new Error("No directory selected.");
  }}

  const fileHandle = await state.dirHandle.getFileHandle(filename, {{ create: true }});
  const writable = await fileHandle.createWritable();
  await writable.write(blob);
  await writable.close();
}}

function downloadBlob(filename, blob) {{
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}}

async function exportSelected() {{
  const grouped = {{}};

  for (const [, v] of state.selected.entries()) {{
    const f = v.finding;
    const fx = v.fix;
    const key = f.id;

    if (!grouped[key]) {{
      grouped[key] = {{
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
      }};
    }}

    grouped[key].selected_fixes.push({{
      fix_id: fx.fix_id,
      fixer_index: fx.fixer_index,
      title: fx.title,
      reason: fx.reason,
      dsl: fx.dsl
    }});
  }}

  const out = {{
    generated_at: new Date().toISOString(),
    selected_count: state.selected.size,
    findings: Object.values(grouped)
  }};

  const filename = "astanalyzer-selected.json";
  const blob = new Blob([JSON.stringify(out, null, 2)], {{ type: "application/json" }});

  try {{
    if (state.dirHandle && hasDirectoryPickerSupport()) {{
      await saveBlobToPickedDirectory(filename, blob);
      setHint(`The file was saved to the selected folder as ${{filename}}.`, "ok");
      return;
    }}

    downloadBlob(filename, blob);
    setHint("The browser used the standard file download.");
  }} catch (err) {{
    console.error(err);
    setHint("Direct save to folder failed. The file will be downloaded normally.");
    downloadBlob(filename, blob);
  }}
}}

fileInput.addEventListener("change", (e) => {{
  const file = e.target.files?.[0];
  if (file) loadFromFile(file);
}});

search.addEventListener("input", (e) => {{
  state.filter = e.target.value;
  render();
}});

btnPickDir.addEventListener("click", () => {{
  pickDirectory();
}});

btnSelectAll.addEventListener("click", () => {{
  state.findings.filter(matchesFilter).forEach(f => {{
    f.fixes.forEach(fx => {{
      state.selected.set(fixKey(f, fx), {{ finding: f, fix: fx }});
    }});
  }});
  updateCounts();
  render();
}});

btnClear.addEventListener("click", () => {{
  state.selected.clear();
  updateCounts();
  render();
}});

btnExport.addEventListener("click", () => {{
  exportSelected();
}});

updateSaveTargetLabel();
applyJson(state.raw, "scan_report.json");
</script>
</body>
</html>"""


def write_report_html(scan_data: dict, output_path: Path) -> Path:
    """Write standalone HTML report to disk and return the output path."""
    html = build_report_html(scan_data)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def open_report_in_browser(report_path: Path) -> None:
    """Open generated HTML report in the default browser."""
    webbrowser.open(report_path.resolve().as_uri(), new=2)