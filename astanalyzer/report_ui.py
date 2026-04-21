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

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer


def highlight_python_code(
    code: str,
    snippet_start_line: int | None = None,
    match_start_line: int | None = None,
    match_end_line: int | None = None,
) -> str:
    """Return syntax-highlighted HTML for a Python code snippet with highlighted match lines."""
    if not code:
        return ""

    lines = code.splitlines()

    leading_blank_count = 0
    for line in lines:
        if line.strip() == "":
            leading_blank_count += 1
        else:
            break

    if leading_blank_count:
        lines = lines[leading_blank_count:]
        code = "\n".join(lines)

    adjusted_snippet_start = (snippet_start_line or 1) + leading_blank_count

    hl_lines: list[int] = []
    if (
        match_start_line is not None
        and match_end_line is not None
    ):
        start_rel = max(1, match_start_line - adjusted_snippet_start + 1)
        end_rel = max(start_rel, match_end_line - adjusted_snippet_start + 1)
        hl_lines = list(range(start_rel, end_rel + 1))

    formatter = HtmlFormatter(
        nowrap=False,
        cssclass="codehilite",
        linenos="table",
        linenostart=adjusted_snippet_start,
        hl_lines=hl_lines,
    )

    return highlight(code, PythonLexer(), formatter)


def build_report_html(report_data: dict) -> str:
    """Build a standalone HTML report page from scan JSON data."""
    report_data = json.loads(json.dumps(report_data))

    findings = report_data.get("findings", [])
    for finding in findings:
        snippet = finding.get("code_snippet", "") or ""
        snippet_start_line = finding.get("snippet_start_line")
        match_start_line = finding.get("start_line")
        match_end_line = finding.get("end_line")

        finding["code_snippet_html"] = (
            highlight_python_code(
                snippet,
                snippet_start_line=snippet_start_line,
                match_start_line=match_start_line,
                match_end_line=match_end_line,
            )
            if snippet
            else ""
        )

    safe_json = (
        json.dumps(report_data, ensure_ascii=False, indent=2)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    pygments_css = HtmlFormatter(cssclass="codehilite").get_style_defs(".codehilite")

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
      padding: 4px 8px;
      border: 1px solid rgba(127,127,127,.35);
      border-radius: 999px;
      font-size: 12px;
      white-space: nowrap;
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
      gap: 12px;
    }}

    .card {{
      border: 1px solid rgba(127,127,127,.25);
      border-radius: 14px;
      background: color-mix(in oklab, Canvas, CanvasText 2%);
      overflow: hidden;
    }}

    .finding {{
      border-radius: 14px;
    }}

    .finding > summary {{
      list-style: none;
      cursor: pointer;
      padding: 14px 16px;
    }}

    .finding > summary::-webkit-details-marker {{
      display: none;
    }}

    .finding > summary:hover {{
      background: color-mix(in oklab, Canvas, CanvasText 3%);
    }}

    .summary-top {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      flex-wrap: wrap;
    }}

    .summary-main {{
      min-width: 0;
      flex: 1;
    }}

    .title {{
      font-weight: 700;
      margin-bottom: 8px;
    }}

    .meta {{
      opacity: .8;
      font-size: 12px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }}

    .path {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      opacity: .85;
      word-break: break-word;
    }}

    .message {{
      margin-top: 8px;
      line-height: 1.45;
      opacity: .95;
      white-space: pre-wrap;
    }}

    .expand-hint {{
      font-size: 12px;
      opacity: .65;
      white-space: nowrap;
    }}

    .detail-body {{
    padding: 12px 16px 16px;
    border-top: 1px solid rgba(127,127,127,.18);
    display: grid;
    gap: 14px;
    }}

    .section {{
      display: grid;
      gap: 8px;
    }}

    .section-title {{
      font-size: 13px;
      font-weight: 700;
      opacity: .82;
      margin-bottom: 2px;
    }}

    .desc {{
      padding: 8px 10px;
      border-left: 3px solid rgba(127,127,127,.35);
      border-radius: 8px;
      background: color-mix(in oklab, Canvas, CanvasText 3%);
      line-height: 1.4;
      white-space: pre-wrap;
    }}

    .tech {{
      font-size: 12px;
      opacity: .75;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}

    .fixes, .actions {{
      display: grid;
      gap: 8px;
    }}

    .fix, .action {{
      border: 1px solid rgba(127,127,127,.18);
      border-radius: 10px;
      padding: 10px;
      display: grid;
      gap: 6px;
      background: color-mix(in oklab, Canvas, CanvasText 2%);
    }}

    .action.ignore {{
      opacity: .85;
      border-style: dashed;
    }}

    .fix label,
    .action label {{
      display: flex;
      gap: 10px;
      align-items: flex-start;
    }}

    .fix-title,
    .action-title {{
      font-weight: 600;
    }}

    .fix-reason,
    .action-reason {{
      opacity: .8;
      font-size: 12px;
      line-height: 1.4;
    }}

    .code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid rgba(127,127,127,.2);
      overflow: auto;
      background: color-mix(in oklab, Canvas, CanvasText 4%);
      white-space: pre-wrap;
      max-height: 220px;
    }}

    .nested-details {{
      border: 1px dashed rgba(127,127,127,.28);
      border-radius: 10px;
      padding: 8px 10px;
    }}

    .nested-details summary {{
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      opacity: .9;
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

    .code-wrap {{
      overflow: auto;
    }}

    .codehilite {{
      margin: 0;
      background: transparent !important;
    }}

    .codehilite pre {{
      margin: 0;
      white-space: pre;
      background: transparent !important;
    }}

    {pygments_css}

    .code {{
      font-size: 13px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(130,160,220,.18);
      overflow: auto;
      background: #2f3136;
      max-height: 380px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.03);
    }}

    .codehilite {{
      margin: 0;
      background: transparent !important;
      color: #e6edf3;
    }}

    .codehilite pre {{
      margin: 0;
      background: transparent !important;
      white-space: pre;
      color: #e6edf3;
      line-height: 1.55;
    }}

    .codehilite,
    .codehilite pre,
    .codehilite code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
    }}

    /* default text */
    .codehilite .n,
    .codehilite .nn,
    .codehilite .nx,
    .codehilite .p,
    .codehilite .w {{
      color: #e6edf3;
    }}

    /* keywords: def, if, try, except */
    .codehilite .k,
    .codehilite .kn,
    .codehilite .kp,
    .codehilite .kr {{
      color: #ffbd59;
      font-weight: 600;
    }}

    /* function / method names */
    .codehilite .nf {{
      color: #2f81f7;
    }}

    /* class names / types */
    .codehilite .nc,
    .codehilite .kt {{
      color: #a5d6ff;
    }}

    /* strings and docstrings */
    .codehilite .s,
    .codehilite .sa,
    .codehilite .sb,
    .codehilite .sc,
    .codehilite .sd,
    .codehilite .s1,
    .codehilite .s2,
    .codehilite .se,
    .codehilite .sh,
    .codehilite .si,
    .codehilite .sr,
    .codehilite .ss,
    .codehilite .dl {{
      color: #7ee787;
      font-style: italic;
    }}

    /* numbers */
    .codehilite .m,
    .codehilite .mb,
    .codehilite .mf,
    .codehilite .mh,
    .codehilite .mi,
    .codehilite .mo {{
      color: #ff9e64;
    }}

    /* comments */
    .codehilite .c,
    .codehilite .c1,
    .codehilite .cm,
    .codehilite .cp,
    .codehilite .cs {{
      color: #8b949e;
      font-style: italic;
    }}

    /* builtins / constants */
    .codehilite .nb,
    .codehilite .bp {{
      color: #a5d6ff;
      font-weight: 500;
    }}

    .codehilite .nb,
    .codehilite .bp,
    .codehilite .fm,
    .codehilite .vc,
    .codehilite .vg,
    .codehilite .vi {{
      color: #b6e3ff;
      font-weight: 500;
    }}

    /* operators */
    .codehilite .o,
    .codehilite .ow {{
      color: #c9d1d9;
    }}

    /* exceptions / special names */
    .codehilite .ne {{
      color: #ff7b72;
      font-weight: 600;
    }}

    .codehilite .hll {{
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 3px 0 0 rgba(180, 200, 255, 0.28);
    }}

    .codehilite table {{
      width: 100%;
      border-collapse: collapse;
      border-spacing: 0;
    }}

    .codehilite td {{
      vertical-align: top;
      padding: 0;
    }}

    .codehilite .linenos {{
      user-select: none;
      opacity: 0.55;
      color: #8b949e;
      border-right: 1px solid rgba(255,255,255,.08);
      padding-right: 12px;
    }}

    .codehilite .linenos pre,
    .codehilite .code pre {{
      margin: 0;
      line-height: 1.55;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
    }}

    .codehilite .code {{
      width: 100%;
    }}

.codehilite .linenos pre {{
  text-align: right;
}}

.codehilite .code {{
  padding-left: 12px;
}}

.codehilite .hll {{
  background: rgba(160, 190, 255, 0.08);
  box-shadow: inset 3px 0 0 rgba(160, 190, 255, 0.35);
}}

  </style>
</head>
<body>
  <header>
    <h1>astanalyzer – fix selection from JSON plan</h1>
    <div class="row">
      <span class="pill" id="status">Loaded</span>
      <span class="pill" id="counts">0 findings / 0 fixes selected / 0 actions selected</span>
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
  <script id="report-data" type="application/json">{safe_json}</script>
<script>

const initialRaw = JSON.parse(
  document.getElementById("report-data").textContent
);

const state = {{
  raw: initialRaw,
  findings: [],
  selected: new Map(),
  selectedActions: new Map(),
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
      code_snippet: f.code_snippet ?? "",
      code_snippet_html: f.code_snippet_html ?? "",
      snippet_start_line: f.snippet_start_line ?? null,
      snippet_end_line: f.snippet_end_line ?? null,
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

function actionKey(finding, actionType) {{
  return `${{finding.file}}::${{finding.id}}::${{actionType}}`;
}}

function updateCounts() {{
  elCounts.textContent =
    `${{state.findings.length}} findings / ` +
    `${{state.selected.size}} fixes selected / ` +
    `${{state.selectedActions.size}} actions selected`;
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
    ...finding.fixes.map(fx => fx.reason),
    "Suppress this warning"
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
  const actions = Array.isArray(dslObj.actions) ? dslObj.actions : [];

  if (actions.length) {{
    actions.forEach((action) => {{
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

    const details = document.createElement("details");
    details.className = "finding";

    const summary = document.createElement("summary");
    summary.innerHTML = `
      <div class="summary-top">
        <div class="summary-main">
          <div class="title">${{escapeHtml(f.title)}}</div>

          <div class="meta">
            <span class="pill" title="Severity">${{escapeHtml(f.severity)}}</span>
            <span class="pill" title="Rule identifier">${{escapeHtml(f.rule_id)}}</span>
          </div>

          <div class="path" title="File and location">
            ${{escapeHtml(f.file)}}${{formatLines(f.start_line, f.end_line)}}
          </div>
        </div>

        <div class="expand-hint">Show details</div>
      </div>
    `;
    details.appendChild(summary);
    details.addEventListener("toggle", () => {{
        const hint = details.querySelector(".expand-hint");
        if (hint) {{
            hint.textContent = details.open ? "Hide details" : "Show details";
        }}
    }});

    const body = document.createElement("div");
    body.className = "detail-body";

    if (f.message) {{
      const messageSection = document.createElement("details");
      messageSection.className = "nested-details";
      messageSection.innerHTML = `
        <summary>Rule description</summary>
        <div class="desc">${{escapeHtml(f.message)}}</div>
      `;
      body.appendChild(messageSection);
    }}
         
    if (f.code_snippet_html) {{
    const codeSection = document.createElement("details");
    codeSection.className = "nested-details";
    codeSection.innerHTML = `
        <summary>View code context</summary>
        <div class="code code-wrap">${{f.code_snippet_html}}</div>
    `;
    body.appendChild(codeSection);
    }}

    const fixesSection = document.createElement("div");
    fixesSection.className = "section";
    fixesSection.innerHTML = `<div class="section-title">Fix proposals</div>`;

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
        const humanText = buildHumanFixText(fx);
        const fixReason =
          fx.reason && fx.reason.trim() !== (f.message || "").trim()
            ? fx.reason
            : "";

        fixDiv.innerHTML = `
          <label>
            <input type="checkbox" ${{checked ? "checked" : ""}} />
            <div>
              <div class="fix-title">${{escapeHtml(fx.title)}}</div>
              ${{
                fixReason
                  ? `<div class="fix-reason">${{escapeHtml(fixReason)}}</div>`
                  : ""
              }}
            </div>
          </label>
        `;

        const cb = fixDiv.querySelector("input");
        cb.addEventListener("change", (e) => {{
          if (e.target.checked) {{
            state.selected.set(k, {{ finding: f, fix: fx }});
          }} else {{
            state.selected.delete(k);
          }}
          updateCounts();
        }});

        if (humanText && humanText.trim() !== (fx.reason || "").trim()) {{
          const desc = document.createElement("div");
          desc.className = "desc";
          desc.textContent = humanText;
          fixDiv.appendChild(desc);
        }}

        const dslText = typeof fx.dsl === "string"
          ? fx.dsl
          : JSON.stringify(fx.dsl, null, 2);

        if (dslText && dslText !== "{{}}" && dslText !== "[]") {{
          const rawDetails = document.createElement("details");
          rawDetails.className = "nested-details";
          rawDetails.innerHTML = `
            <summary>Technical detail</summary>
            <div class="code">${{escapeHtml(dslText)}}</div>
          `;
          fixDiv.appendChild(rawDetails);
        }}

        fixesWrap.appendChild(fixDiv);
      }});
    }}

    fixesSection.appendChild(fixesWrap);
    body.appendChild(fixesSection);

    const actionsSection = document.createElement("div");
    actionsSection.className = "section";
    actionsSection.innerHTML = `<div class="section-title">Additional actions</div>`;

    const actionsWrap = document.createElement("div");
    actionsWrap.className = "actions";

    const ignoreDiv = document.createElement("div");
    ignoreDiv.className = "action ignore";

    const ignoreKey = actionKey(f, "ignore_finding");
    const ignoreChecked = state.selectedActions.has(ignoreKey);

    ignoreDiv.innerHTML = `
      <label>
        <input type="checkbox" ${{ignoreChecked ? "checked" : ""}} />
        <div>
          <div class="action-title">Suppress this warning</div>
          <div class="action-reason">
            Insert ignore marker for ${{escapeHtml(f.rule_id)}} in this location.
          </div>
        </div>
      </label>
    `;

    const ignoreCb = ignoreDiv.querySelector("input");
    ignoreCb.addEventListener("change", (e) => {{
      if (e.target.checked) {{
        state.selectedActions.set(ignoreKey, {{
          type: "ignore_finding",
          finding: f
        }});
      }} else {{
        state.selectedActions.delete(ignoreKey);
      }}
      updateCounts();
    }});

    actionsWrap.appendChild(ignoreDiv);
    actionsSection.appendChild(actionsWrap);
    body.appendChild(actionsSection);

    details.appendChild(body);
    card.appendChild(details);
    elList.appendChild(card);
  }});

  elStatus.textContent = state.raw ? "Loaded" : "No data";
  updateCounts();
}}

function applyJson(json, source) {{
  state.raw = json;
  state.findings = normalisePlan(json);
  state.selected.clear();
  state.selectedActions.clear();
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
  const selectedActions = [];

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

  for (const [, v] of state.selectedActions.entries()) {{
    const f = v.finding;
    selectedActions.push({{
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
    }});
  }}

  const out = {{
    generated_at: new Date().toISOString(),
    project_root: state.raw?.project_root ?? null,
    selected_fix_count: state.selected.size,
    selected_action_count: state.selectedActions.size,
    findings: Object.values(grouped),
    selected_actions: selectedActions
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
  state.selectedActions.clear();
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
