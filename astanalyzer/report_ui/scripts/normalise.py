def build_script_data_normalisation() -> str:
    return """
function normalisePlan(json) {
  const findings = Array.isArray(json)
    ? json
    : (json.findings ?? json.results ?? json.items ?? []);

  if (!Array.isArray(findings)) return [];

  return findings.map((f, idx) => {
    const fixes = f.fixes ?? f.fix_proposals ?? f.proposals ?? f.selected_fixes ?? [];
    const ruleId = f.rule_id ?? f.rule ?? f.code ?? "UNKNOWN_RULE";

    return {
      _idx: idx,
      id: f.id ?? f.finding_id ?? f.match_id ?? `${idx}`,
      rule_id: ruleId,
      category: f.category ?? getCategoryFromRuleId(ruleId),
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
      snippet_truncated: f.snippet_truncated ?? false,
      anchor: f.anchor ?? null,
      raw_finding: f,
      fixes: Array.isArray(fixes) ? fixes.map((x, j) => ({
        _jdx: j,
        fix_id: x.fix_id ?? x.id ?? `${idx}:${j}`,
        fixer_index: x.fixer_index ?? x.index ?? j,
        title: x.title ?? x.name ?? "Fix",
        reason: x.reason ?? x.because ?? x.note ?? "",
        dsl: x.dsl ?? x.plan ?? x.actions ?? x,
        patch_preview: x.patch_preview ?? x.patch ?? x.preview ?? "",
        raw_fix: x
      })) : []
    };
  });
}

function getCategoryFromRuleId(ruleId) {
  if (!ruleId) return "OTHER";
  const parts = String(ruleId).split("-");
  return parts[0] || "OTHER";
}
"""