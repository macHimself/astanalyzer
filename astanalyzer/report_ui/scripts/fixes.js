function fixKey(finding, fix) {
  return `${finding.file}::${finding.id}::${fix.fix_id}`;
}

function actionKey(finding, actionType) {
  return `${finding.file}::${finding.id}::${actionType}`;
}

function normaliseDslObject(dsl) {
  if (!dsl) return null;

  if (typeof dsl === "string") {
    try {
      return JSON.parse(dsl);
    } catch {
      return { raw: dsl };
    }
  }

  if (Array.isArray(dsl)) {
    return { actions: dsl };
  }

  if (typeof dsl === "object") {
    return dsl;
  }

  return { raw: String(dsl) };
}

function describeAction(action) {
  const op = action?.op ?? "unknown_op";
  const text = action?.text ?? "";
  const ref = action?.ref ?? action?.target_ref ?? "";
  const label = action?.label ?? action?.title ?? action?.summary ?? action?.description ?? "";
  const note = action?.comment ?? action?.reason ?? "";

  switch (op) {
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
  }
}

function buildHumanFixText(fx) {
  const dslObj = normaliseDslObject(fx.dsl);
  if (!dslObj) return "";

  const lines = [];
  const actions = Array.isArray(dslObj.actions) ? dslObj.actions : [];

  if (actions.length) {
    actions.forEach((action) => {
      let step = action.summary || action.label || action.note || describeAction(action);
      const extraNote = action?.comment ?? action?.reason ?? "";
      if (extraNote) {
        step += " Note: " + extraNote;
      }
      lines.push(step);
    });
  }

  return lines.join("\\n");
}

function shortFixSummary(fx) {
  const text = buildHumanFixText(fx).trim();

  if (!text) return "Review proposed change";
  if (text.length <= 90) return text;

  return text.slice(0, 87).trimEnd() + "…";
}

function removeSelectedFixesForFinding(finding) {
  for (const [key, value] of state.selected.entries()) {
    if (value.finding.id === finding.id && value.finding.file === finding.file) {
      state.selected.delete(key);
    }
  }
}