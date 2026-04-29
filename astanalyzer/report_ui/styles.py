def build_report_styles(pygments_css: str) -> str:
    return f"""
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
      max-width: 1200px;
      margin: 0 auto;
    }}

    .toolbar {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 10px 0;
      align-items: center;
    }}

    .toolbar-main {{
      margin-top: 18px;
    }}

    .toolbar-view {{
      margin-top: 8px;
    }}

    .toolbar-selection {{
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid rgba(127,127,127,.14);
    }}

    .toolbar input[type="search"] {{
      flex: 1;
      min-width: 320px;
    }}

    .toolbar-selection button {{
      min-width:120px;
    }}

    .view-toggle {{
      display: inline-flex;
      gap: 0;
      border: 1px solid rgba(127,127,127,.35);
      border-radius: 10px;
      overflow: hidden;
    }}

    .view-toggle button {{
      border: 0;
      border-radius: 0;
    }}

    .view-toggle button.active {{
      background: color-mix(in oklab, CanvasText 12%, Canvas);
      font-weight: 700;
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
      border: 1px solid rgba(127,127,127,.16);
      border-radius: 10px;
      border-color: rgba(127,127,127,.18);
      background: color-mix(in oklab, Canvas, CanvasText 2%);
      overflow: hidden;
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
      padding: 10px 12px 12px;
      display: grid;
      gap: 14px;
      border-top: 0;
    }}

    .section {{
      display: grid;
      gap: 8px;
    }}

    .desc {{
      padding: 6px 0;
      border-left: none;
      border-radius: 0;
      background: transparent;
      opacity: 0.8;
      font-size: 13px;
    }}

    .rule-description {{      
      border-style: solid;
      background: color-mix(in oklab, Canvas, CanvasText 3%);
    }}
    
    .rule-expl {{      
      display: grid;
      gap: 10px;
      margin-top: 8px;
    }}
    
    .expl-section {{      
      padding: 8px 10px;
      border: 1px solid rgba(127,127,127,.16);
      border-radius: 9px;
      background: color-mix(in oklab, Canvas, CanvasText 2%);
    }}

    .expl-title {{      
      font-size: 12px;
      font-weight: 700;
      opacity: .9;
      margin-bottom: 4px;
    }}
    
    .expl-text {{      
      font-size: 13px;
      line-height: 1.45;
      opacity: .86;
    }}
    
    .expl-why {{      
      border-left: 3px solid #d99a00;
      padding-left: 9px;
    }}

    .expl-limitations {{
      border-left: 3px solid #777;
      padding-left: 9px;
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

    .action-reason {{
      opacity: .8;
      font-size: 12px;
      line-height: 1.4;
    }}

    .fix-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
    }}

    .code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,.10);
      overflow: auto;
      background: #2f3136;
      max-height: 380px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.03);
      overflow-clip-margin: padding-box;
    }}

    .nested-details {{
      border: 1px dashed rgba(127,127,127,.18);
      border-radius: 10px;
      padding: 7px 9px;
    }}

    .nested-details summary {{
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      opacity: .9;
      user-select: none;
      list-style: none;
    }}

    .nested-details summary::selection {{
      background: transparent;
    }}

    footer {{
      padding: 18px 20px;
      opacity: .75;
      font-size: 12px;
      text-align: center;
    }}

    .ok {{
      color: #166534;
    }}

    .code-wrap {{
      overflow: auto;
      max-width: 100%;
      box-sizing: border-box;
      border-radius: 14px;
      overflow: auto;
    }}

    .codehilite {{
      margin: 0;
      background: transparent !important;
      min-width: max-content;
      color: #e6edf3;
    }}

    .codehilite pre {{
      margin: 0;
      white-space: pre;
      background: transparent !important;
      color: #e6edf3;
      line-height: 1.55;
    }}

    .codehilite,
    .codehilite pre,
    .codehilite code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
    }}

    {pygments_css}

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

    .codehilite .linenos pre {{
      text-align: right;
    }}

    .codehilite .code {{
      width: 100%;
      padding-left: 12px;
    }}

    .codehilite .n,
    .codehilite .nn,
    .codehilite .nx,
    .codehilite .p,
    .codehilite .w {{
      color: #e6edf3;
    }}

    .codehilite .k,
    .codehilite .kn,
    .codehilite .kp,
    .codehilite .kr {{
      color: #ffbd59;
      font-weight: 600;
    }}

    .codehilite .nf {{
      color: #2f81f7;
    }}

    .codehilite .nc,
    .codehilite .kt {{
      color: #a5d6ff;
    }}

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

    .codehilite .m,
    .codehilite .mb,
    .codehilite .mf,
    .codehilite .mh,
    .codehilite .mi,
    .codehilite .mo {{
      color: #ff9e64;
    }}

    .codehilite .c,
    .codehilite .c1,
    .codehilite .cm,
    .codehilite .cp,
    .codehilite .cs {{
      color: #8b949e;
      font-style: italic;
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

    .codehilite .o,
    .codehilite .ow {{
      color: #c9d1d9;
    }}

    .codehilite .ne {{
      color: #ff7b72;
      font-weight: 600;
    }}

    .codehilite .hll {{
      background: rgba(255,255,255,.07);
      box-shadow: inset 3px 0 0 rgba(180, 200, 255, 0.28);
    }}

    .group {{
      border: 1px solid rgba(127,127,127,.22);
      border-radius: 10px;
      border-color: rgba(127,127,127,.18);
      background: color-mix(in oklab, Canvas, CanvasText 1.5%);
      overflow: hidden;
    }}

    .group > summary {{
      list-style: none;
      cursor: pointer;
      padding: 14px 16px;
      user-select: none;
      border-bottom: 0;
    }}

    .group > summary:hover {{
      background: color-mix(in oklab, Canvas, CanvasText 3%);
    }}

    .group-body {{
      padding: 8px 10px 10px;
      display: grid;
      gap: 8px;
      border-top: 0;
    }}

    .group-summary {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }}

    .group-title {{
      font-weight: 700;
    }}

    .group-meta {{
      font-size: 12px;
      opacity: .7;
      white-space: nowrap;
    }}

    .category-group {{
      background: color-mix(in oklab, Canvas, CanvasText 2%);
    }}

    .category-group .group-title {{
      font-size: 15px;
    }}

    .file-group .group-title {{
      background: transparent;
      font-weight: 600;
      font-size: 13px;
      font-family: ui-monospace, SFMono-Regular,  Menlo, Monaco, Consolas, monospace;
      word-break: break-word;
      padding: 4px 0;
      border-radius: 0;
    }}

    .hint {{
      font-size: 13px;
      opacity: 0.7;
      margin: 12px 0 16px;
    }}

    .info {{
      color: #6b7280;
    }}

    .warn {{
      color: #f59e0b;
      font-weight: 600;
    }}

    .error {{
      color: #dc2626;
      font-weight: 700;
    }}

    .category-warning {{
      border-left: none;
    }}

    .category-error {{
      border-left: none;
    }}

    .rule-warning {{
      border-left: 1px solid #f59e0b;
    }}

    .rule-error {{
      border-left: 1px solid #dc2626;
    }}

    .file-warning {{
      border-left: none;
    }}

    .file-error {{
      border-left: none;
    }}

    .snippet-marker {{
      font-size: 12px;
      opacity: 0.6;
      margin: 6px 0 6px;
      padding-left: 4px;
      border-left: 2px solid rgba(255,255,255,.10);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}

    .code.diff-preview {{
      padding: 10px 12px;
      white-space: pre;
      line-height: 1.5;
      max-width: 100%;
      box-sizing: border-box;
      border-radius: 14px;
      overflow: auto;
      overflow-x: auto;
    }}

    .code.diff-preview pre {{
      margin: 0;
      white-space: pre;
      font: inherit;
      color: inherit;
      background: transparent;
      min-width: max-content;
    }}

    .code.diff-preview div {{
      white-space: pre;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    .code.diff-preview .line-add {{
      color: #9be9a8;
    }}

    .code.diff-preview .line-del {{
      color: #ffb3b3;
    }}

    .code.diff-preview .line-meta {{
      color: #8b949e;
    }}

    .code.diff-preview .line-hunk {{
      color: #79c0ff;
    }}

    .line-range {{
      margin-left: 10px;
      font-size: 12px;
      font-weight: 500;
      opacity: .7;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}

    summary,
    details > summary,
    .nested-details > summary,
    .group > summary {{
      list-style: none;
      outline: none;
    }}

    summary::-webkit-details-marker,
    details > summary::-webkit-details-marker,
    .nested-details > summary::-webkit-details-marker,
    .group > summary::-webkit-details-marker,
    .finding > summary::-webkit-details-marker {{
      display: none;
    }}

    summary::marker,
    details > summary::marker,
    .nested-details > summary::marker,
    .group > summary::marker,
    .finding > summary::marker {{
      content: "";
      font-size: 0;
    }}

    details:focus,
    details:focus-visible,
    summary:focus,
    summary:focus-visible {{
      outline: none;
    }}

    .code-container {{
      position: relative;
    }}

    .copy-code-btn {{
      position: absolute;
      top: 10px;
      right: 12px;
      z-index: 2;
      font-size: 12px;
      padding: 4px 9px;
      border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(0,0,0,0.25);
      backdrop-filter: blur(4px);
      opacity: 0.85;
      transition: all 0.15s ease;
    }}

    .copy-code-btn:hover {{
      opacity: 1;
      color: #f59e0b;
      border-color: rgba(245,158,11,0.5);
      background: rgba(0,0,0,0.4);
    }}

    .copy-code-btn.copied {{
      background: #2ecc71;
      color: black;
    }}

  </style>
"""
