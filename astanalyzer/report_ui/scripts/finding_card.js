function buildFindingCard(f) {
  const card = document.createElement("div");
  card.className = "card";

  const details = document.createElement("details");
  details.className = "nested-details";
  details.dataset.detailsKey = `finding::${f.file}::${f.id}`;

  const summary = document.createElement("summary");
  summary.innerHTML = `
    <div class="summary-top">
      <div class="summary-main">
        <div class="title">${escapeHtml(f.id)}
          <span class="line-range">${formatLineRange(f.start_line, f.end_line)}</span>
        </div>
      </div>
      <div class="expand-hint">Show details</div>
    </div>
  `;
  details.appendChild(summary);

  details.addEventListener("toggle", () => {
    const hint = details.querySelector(".expand-hint");
    if (hint) {
      hint.textContent = details.open ? "Hide details" : "Show details";
    }
  });

  const body = document.createElement("div");
  body.className = "detail-body";

  if (f.code_snippet_html) {
    const codeSection = document.createElement("details");
    codeSection.className = "nested-details";
    codeSection.dataset.detailsKey = `code::${f.file}::${f.id}`;
    const marker = f.snippet_truncated
      ? `<div class="snippet-marker">… truncated …</div>`
      : "";
    codeSection.innerHTML = `
      <summary>View code context</summary>
      ${marker}
      <div class="code-container">
        <button type="button" class="copy-code-btn">Copy code</button>
        <div class="code code-wrap" data-snippet-loaded="false"></div>
      </div>
    `;

    const copyCodeBtn = codeSection.querySelector(".copy-code-btn");

    copyCodeBtn.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();

      try {
        await navigator.clipboard.writeText(f.code_snippet || "");
        copyCodeBtn.textContent = "Copied";
        setTimeout(() => {
        copyCodeBtn.textContent = "Copy code";
        }, 1200);
      } catch (err) {
        console.error(err);
        copyCodeBtn.textContent = "Copy failed";
        setTimeout(() => {
        copyCodeBtn.textContent = "Copy code";
        }, 1200);
      }
    });

    codeSection.addEventListener("toggle", () => {
      const target = codeSection.querySelector(".code-wrap");
      if (!codeSection.open || !target || target.dataset.snippetLoaded === "true") {
        return;
      }

      target.innerHTML = f.code_snippet_html;
      target.dataset.snippetLoaded = "true";
    });

    body.appendChild(codeSection);
  }

  const fixesSection = document.createElement("details");
  fixesSection.className = "nested-details section";
  fixesSection.dataset.detailsKey = `fixes::${f.file}::${f.id}`;
  fixesSection.innerHTML = `<summary>Fix proposals</summary>`;

  const fixesWrap = document.createElement("div");
  fixesWrap.className = "fixes";

  if (!f.fixes.length) {
    const none = document.createElement("div");
    none.className = "fix";
    none.textContent = "No fix proposals in this finding.";
    fixesWrap.appendChild(none);
  } else {
    f.fixes.forEach((fx) => {
      const k = fixKey(f, fx);
      const fixDiv = document.createElement("div");
      fixDiv.className = "fix";

      const checked = state.selected.has(k);

      fixDiv.innerHTML = `
        <label class="fix-header" title="Select this fix">
          <input type="checkbox" ${checked ? "checked" : ""} />
          <div class="fix-main">
            <div class="fix-title">
              Proposed fix: ${escapeHtml(shortFixSummary(fx))}
            </div>
          </div>
        </label>
      `;

      const cb = fixDiv.querySelector("input");

      cb.addEventListener("change", (e) => {
        if (e.target.checked) {
          removeSelectedFixesForFinding(f);

          fixDiv.parentElement
            .querySelectorAll('input[type="checkbox"]')
            .forEach((input) => {
              if (input !== e.target) {
                input.checked = false;
              }
            });

          state.selected.set(k, { finding: f, fix: fx });
        } else {
          state.selected.delete(k);
        }

        updateCounts();
      });

      const patchPreviewText = (fx.patch_preview || "").trim();
      const patchPreviewStatus =
        fx.raw_fix?.patch_preview_status || (patchPreviewText ? "available" : "unavailable");
      const patchPreviewError = fx.raw_fix?.patch_preview_error || "";

      const patchSummaryLabel =
        patchPreviewStatus === "available"
          ? "Patch preview"
          : "Patch preview unavailable";

      if (patchPreviewText || patchPreviewError) {
        const patchDetails = document.createElement("details");
        patchDetails.className = "nested-details";
        patchDetails.dataset.detailsKey = `patch::${k}`;
        if (patchPreviewText) {
          patchDetails.innerHTML = `
            <summary>${escapeHtml(patchSummaryLabel)}</summary>
            <div class="code diff-preview">
              ${renderDiff(patchPreviewText)}
            </div>
          `;
        } else {
          patchDetails.innerHTML = `
            <summary>${escapeHtml(patchSummaryLabel)}</summary>
            <div class="desc">Preview unavailable.${patchPreviewError ? " " + escapeHtml(patchPreviewError) : ""}</div>
          `;
        }
        fixDiv.appendChild(patchDetails);
      }

      fixesWrap.appendChild(fixDiv);
    });
  }

  fixesSection.appendChild(fixesWrap);
  body.appendChild(fixesSection);

  const actionsSection = document.createElement("details");
  actionsSection.className = "nested-details section";
  actionsSection.innerHTML = `<summary>Additional actions</summary>`;

  const actionsWrap = document.createElement("div");
  actionsWrap.className = "actions";

  const ignoreDiv = document.createElement("div");
  ignoreDiv.className = "action ignore";

  const ignoreKey = actionKey(f, "ignore_finding");
  const ignoreChecked = state.selectedActions.has(ignoreKey);

  ignoreDiv.innerHTML = `
    <label>
      <input type="checkbox" ${ignoreChecked ? "checked" : ""} />
      <div>
        <div class="action-title">Suppress this warning</div>
        <div class="action-reason">
          Insert ignore marker for ${escapeHtml(f.rule_id)} in this location.
        </div>
      </div>
    </label>
  `;

  const ignoreCb = ignoreDiv.querySelector("input");
  ignoreCb.addEventListener("change", (e) => {
    if (e.target.checked) {
      state.selectedActions.set(ignoreKey, {
        type: "ignore_finding",
        finding: f
      });
    } else {
      state.selectedActions.delete(ignoreKey);
    }
    updateCounts();
  });

  actionsWrap.appendChild(ignoreDiv);
  actionsSection.appendChild(actionsWrap);
  body.appendChild(actionsSection);

  details.appendChild(body);
  card.appendChild(details);

  return card;
}