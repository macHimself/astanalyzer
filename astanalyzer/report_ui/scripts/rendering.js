function renderRuleFirst(visible) {
  const grouped = groupFindingsRuleFirst(visible);

  grouped.forEach((cat) => {
    const categoryCounts = countSeverity(cat.findings);
    const categoryMeta = formatSeverityMeta(categoryCounts);

    const { details: categoryDetails, body: categoryBody } = createGroupDetails(
      "category-group",
      escapeHtml(formatCategoryLabel(cat.category)),
      `${cat.findings.length} findings${categoryMeta ? ` • ${categoryMeta}` : ""}`,
      categoryCounts
    );

    cat.rules.forEach((rule) => {
      const ruleCounts = countSeverity(rule.findings);
      const ruleMeta = formatSingleSeverityMeta(rule.findings);

      const { details: ruleDetails, body: ruleBody } = createGroupDetails(
        "rule-group",
        `${escapeHtml(rule.rule_id || "UNKNOWN_RULE")} – ${escapeHtml(rule.title || "Untitled rule")}`,
        ruleMeta,
        ruleCounts
      );

      ruleDetails.dataset.rendered = "false";
      ruleDetails.addEventListener("toggle", () => {
        if (!ruleDetails.open || ruleDetails.dataset.rendered === "true") {
          return;
        }

        const ruleDescription = rule.findings[0]?.message?.trim();
        if (ruleDescription) {
          const descDetails = document.createElement("details");
          descDetails.className = "nested-details";
          descDetails.innerHTML = `
            <summary>Rule description</summary>
            <div class="desc">${escapeHtml(ruleDescription)}</div>
          `;
          ruleBody.appendChild(descDetails);
        }

        rule.files.forEach((fileItem) => {
          ruleBody.appendChild(buildFileGroup(fileItem.file, fileItem.findings));
        });

        ruleDetails.dataset.rendered = "true";
      });

      categoryBody.appendChild(ruleDetails);
    });

    elList.appendChild(categoryDetails);
  });
}

function renderFileFirst(visible) {
  const grouped = groupFindingsFileFirst(visible);

  grouped.forEach((fileItem) => {
    const fileCounts = countSeverity(fileItem.findings);
    const fileMeta = formatSeverityMeta(fileCounts);

    const { details: fileDetails, body: fileBody } = createGroupDetails(
      "file-group",
      escapeHtml(fileItem.file),
      `${fileItem.findings.length} findings${fileMeta ? ` • ${fileMeta}` : ""}`,
      fileCounts
    );

    fileItem.categories.forEach((categoryItem) => {
      const categoryCounts = countSeverity(categoryItem.findings);
      const categoryMeta = formatSeverityMeta(categoryCounts);

      const { details: categoryDetails, body: categoryBody } = createGroupDetails(
        "category-group",
        escapeHtml(formatCategoryLabel(categoryItem.category)),
        `${categoryItem.findings.length} findings${categoryMeta ? ` • ${categoryMeta}` : ""}`,
        categoryCounts
      );

      categoryItem.rules.forEach((rule) => {
        const ruleCounts = countSeverity(rule.findings);
        const ruleMeta = formatSingleSeverityMeta(rule.findings);

        const { details: ruleDetails, body: ruleBody } = createGroupDetails(
          "rule-group",
          `${escapeHtml(rule.rule_id || "UNKNOWN_RULE")} – ${escapeHtml(rule.title || "Untitled rule")}`,
          ruleMeta,
          ruleCounts
        );

        ruleDetails.dataset.rendered = "false";
        ruleDetails.addEventListener("toggle", () => {
          if (!ruleDetails.open || ruleDetails.dataset.rendered === "true") {
            return;
          }

          const ruleDescription = rule.findings[0]?.message?.trim();
          if (ruleDescription) {
            const descDetails = document.createElement("details");
            descDetails.className = "nested-details";
            descDetails.innerHTML = `
              <summary>Rule description</summary>
              <div class="desc">${escapeHtml(ruleDescription)}</div>
            `;
            ruleBody.appendChild(descDetails);
          }

          rule.findings.forEach((f) => {
            ruleBody.appendChild(buildFindingCard(f));
          });

          ruleDetails.dataset.rendered = "true";
        });

        categoryBody.appendChild(ruleDetails);
      });

      fileBody.appendChild(categoryDetails);
    });

    elList.appendChild(fileDetails);
  });
}

function render() {
  elList.innerHTML = "";
  const visible = state.findings.filter(matchesFilter);

  if (state.viewMode === "file-first") {
    renderFileFirst(visible);
  } else {
    renderRuleFirst(visible);
  }

  elStatus.textContent = state.raw ? "Loaded" : "No data";
  updateCounts();
  updateViewButtons();
}

function applyJson(json, source) {
  state.raw = json;
  state.findings = normalisePlan(json);
  state.selected.clear();
  state.selectedActions.clear();
  elSourceHint.textContent = source ?? "JSON";
  enableButtons(true);
  render();
}

function detailsKey(details) {
  if (details.dataset.detailsKey) {
    return details.dataset.detailsKey;
  }

  const title = details.querySelector(":scope > summary")?.textContent?.trim() || "";
  return `${details.className}::${title}`;
}

function rememberDetailsState() {
  const detailsState = new Map();

  document.querySelectorAll("details").forEach((details) => {
    detailsState.set(detailsKey(details), details.open);
  });

  return detailsState;
}

function restoreDetailsState(detailsState) {
  for (let pass = 0; pass < 5; pass++) {
    document.querySelectorAll("details").forEach((details) => {
      const key = detailsKey(details);

      if (detailsState.has(key)) {
        const shouldBeOpen = detailsState.get(key);

        if (details.open !== shouldBeOpen) {
          details.open = shouldBeOpen;
          details.dispatchEvent(new Event("toggle"));
        }
      }
    });
  }
}

function rerenderKeepingDetailsState() {
  const detailsState = rememberDetailsState();
  render();

  requestAnimationFrame(() => {
    restoreDetailsState(detailsState);

    requestAnimationFrame(() => {
      restoreDetailsState(detailsState);
    });
  });
}