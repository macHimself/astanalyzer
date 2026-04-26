function formatCategoryLabel(category) {
  const code = String(category || "OTHER").toUpperCase();
  const label = CATEGORY_LABELS[code];
  return label ? `${code} – ${label}` : code;
}

function countSeverity(findings) {
  let info = 0;
  let warning = 0;
  let error = 0;

  findings.forEach(f => {
    const s = (f.severity || "").toLowerCase();
    if (s === "error") error++;
    else if (s === "warning") warning++;
    else info++;
  });

  return { info, warning, error };
}

function formatSeverityMeta(counts) {
  const parts = [];

  if (counts.info > 0) {
    parts.push(`<span class="info">${counts.info} info</span>`);
  }
  if (counts.warning > 0) {
    parts.push(`<span class="warn">${counts.warning} warning</span>`);
  }
  if (counts.error > 0) {
    parts.push(`<span class="error">${counts.error} error</span>`);
  }

  return parts.join(" • ");
}

function formatSingleSeverityMeta(findings) {
  const counts = countSeverity(findings);

  if (counts.error > 0) {
    return `<span class="error">${counts.error} error${counts.error === 1 ? "" : "s"}</span>`;
  }

  if (counts.warning > 0) {
    return `<span class="warn">${counts.warning} warning${counts.warning === 1 ? "" : "s"}</span>`;
  }

  return `<span class="info">${counts.info} info</span>`;
}

function formatLines(s, e) {
  if (!s && !e) return "";
  if (s && e && s !== e) return `:${s}-${e}`;
  return `:${s ?? e}`;
}

function formatLineRange(s, e) {
  if (!s && !e) return "";
  if (s && e && s !== e) return `lines ${s}-${e}`;
  return `line ${s ?? e}`;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, s => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[s]));
}

function renderDiff(diffText) {
  const lines = diffText.split("\\n");

  return lines.map(line => {
    let cls = "";

    if (line.startsWith("+++ ") || line.startsWith("--- ")) {
      cls = "line-meta";
    } else if (line.startsWith("@@")) {
      cls = "line-hunk";
    } else if (line.startsWith("+")) {
      cls = "line-add";
    } else if (line.startsWith("-")) {
      cls = "line-del";
    }

    return `<div class="${cls}">${escapeHtml(line)}</div>`;
  }).join("");
}