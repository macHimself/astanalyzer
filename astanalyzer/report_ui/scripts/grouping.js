function groupFindingsRuleFirst(findings) {
  const root = new Map();

  findings.forEach((f) => {
    const category = f.category || getCategoryFromRuleId(f.rule_id);
    const ruleKey = f.rule_id || "UNKNOWN_RULE";
    const fileKey = f.file || "unknown";

    if (!root.has(category)) {
      root.set(category, new Map());
    }

    const categoryMap = root.get(category);

    if (!categoryMap.has(ruleKey)) {
      categoryMap.set(ruleKey, new Map());
    }

    const ruleMap = categoryMap.get(ruleKey);

    if (!ruleMap.has(fileKey)) {
      ruleMap.set(fileKey, []);
    }

    ruleMap.get(fileKey).push(f);
  });

  return Array.from(root.entries())
    .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
    .map(([category, rulesMap]) => {
      const rules = Array.from(rulesMap.entries())
        .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
        .map(([ruleId, filesMap]) => {
          const files = Array.from(filesMap.entries())
            .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
            .map(([file, fileFindings]) => ({
              file,
              findings: fileFindings.sort((a, b) => (a.start_line || 0) - (b.start_line || 0))
            }));

          const allFindings = files.flatMap(item => item.findings);
          return {
            rule_id: ruleId,
            title: allFindings[0]?.title || "Untitled rule",
            files,
            findings: allFindings
          };
        });

      const allFindings = rules.flatMap(rule => rule.findings);
      return {
        category,
        rules,
        findings: allFindings
      };
    });
}

function groupFindingsFileFirst(findings) {
  const root = new Map();

  findings.forEach((f) => {
    const fileKey = f.file || "unknown";
    const category = f.category || getCategoryFromRuleId(f.rule_id);
    const ruleKey = f.rule_id || "UNKNOWN_RULE";

    if (!root.has(fileKey)) {
      root.set(fileKey, new Map());
    }

    const fileMap = root.get(fileKey);

    if (!fileMap.has(category)) {
      fileMap.set(category, new Map());
    }

    const categoryMap = fileMap.get(category);

    if (!categoryMap.has(ruleKey)) {
      categoryMap.set(ruleKey, []);
    }

    categoryMap.get(ruleKey).push(f);
  });

  return Array.from(root.entries())
    .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
    .map(([file, categoriesMap]) => {
      const categories = Array.from(categoriesMap.entries())
        .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
        .map(([category, rulesMap]) => {
          const rules = Array.from(rulesMap.entries())
            .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
            .map(([ruleId, ruleFindings]) => ({
              rule_id: ruleId,
              title: ruleFindings[0]?.title || "Untitled rule",
              findings: ruleFindings.sort((a, b) => (a.start_line || 0) - (b.start_line || 0))
            }));

          const allFindings = rules.flatMap(rule => rule.findings);
          return {
            category,
            rules,
            findings: allFindings
          };
        });

      const allFindings = categories.flatMap(category => category.findings);
      return {
        file,
        categories,
        findings: allFindings
      };
    });
}

function createGroupDetails(className, titleHtml, metaHtml, counts, defaultOpen = false) {
  const details = document.createElement("details");
  details.className = `group ${className}`;
  details.open = defaultOpen;

  if (counts.error > 0) {
    if (className.includes("category-group")) details.classList.add("category-error");
    if (className.includes("rule-group")) details.classList.add("rule-error");
    if (className.includes("file-group")) details.classList.add("file-error");
  } else if (counts.warning > 0) {
    if (className.includes("category-group")) details.classList.add("category-warning");
    if (className.includes("rule-group")) details.classList.add("rule-warning");
    if (className.includes("file-group")) details.classList.add("file-warning");
  }

  details.innerHTML = `
    <summary>
      <div class="group-summary">
        <div class="group-title">${titleHtml}</div>
        <div class="group-meta">${metaHtml}</div>
      </div>
    </summary>
  `;

  const body = document.createElement("div");
  body.className = "group-body";
  details.appendChild(body);
  return { details, body };
}

function buildFileGroup(fileLabel, findings) {
  const counts = countSeverity(findings);
  const fileMeta = formatSingleSeverityMeta(findings);

  const { details, body } = createGroupDetails(
    "file-group",
    escapeHtml(fileLabel),
    fileMeta,
    counts
  );

  details.dataset.rendered = "false";
  details.addEventListener("toggle", () => {
    if (!details.open || details.dataset.rendered === "true") {
      return;
    }

    findings.forEach((f) => {
      body.appendChild(buildFindingCard(f));
    });

    details.dataset.rendered = "true";
  });

  return details;
}