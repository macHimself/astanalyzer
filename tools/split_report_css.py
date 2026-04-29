"""
One-time migration script.

Used to split monolithic CSS from build_report_styles()
into modular CSS files.

Not part of runtime.
Not maintained.
"""

from pathlib import Path
import textwrap

SOURCE = Path("astanalyzer/report_ui/styles_old.py")
OUT_DIR = Path("astanalyzer/report_ui/styles")
OUT_DIR.mkdir(parents=True, exist_ok=True)

STYLE_FILES = {
    "base.css": [],
    "toolbar.css": [],
    "findings.css": [],
    "rule_explanation.css": [],
    "fixes.css": [],
    "code.css": [],
    "pygments_overrides.css": [],
    "groups.css": [],
    "diff.css": [],
    "details.css": [],
    "copy_button.css": [],
    "misc.css": [],
}

text = SOURCE.read_text(encoding="utf-8")
css = text.split("<style>", 1)[1].split("</style>", 1)[0]
css = textwrap.dedent(css)
css = css.replace("{{", "{").replace("}}", "}")

css = "\n".join(
    line for line in css.splitlines()
    if "{pygments_css}" not in line
).strip()


def parse_blocks(css_text: str) -> list[str]:
    blocks = []
    i = 0

    while i < len(css_text):
        while i < len(css_text) and css_text[i].isspace():
            i += 1

        if i >= len(css_text):
            break

        start = i
        depth = 0

        while i < len(css_text):
            if css_text[i] == "{":
                depth += 1
            elif css_text[i] == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1

        block = css_text[start:i].strip()
        if block:
            blocks.append(block)

    return blocks


def selector(block: str) -> str:
    return block.split("{", 1)[0].strip()


def target_file(sel: str) -> str:
    if (
        sel.startswith(":root")
        or sel.startswith("body")
        or sel.startswith("header")
        or sel.startswith("h1")
        or sel.startswith("footer")
        or sel in {".ok", ".hint", ".info", ".warn", ".error"}
        or sel.startswith("main")
        or sel.startswith(".grid")
        or sel.startswith(".row")
        or sel.startswith(".pill")
    ):
        return "base.css"

    if (
        sel.startswith(".toolbar")
        or sel.startswith(".view-toggle")
        or sel.startswith("button")
        or sel.startswith("input")
    ):
        return "toolbar.css"

    if (
        sel.startswith(".card")
        or sel.startswith(".summary")
        or sel.startswith(".title")
        or sel.startswith(".meta")
        or sel.startswith(".path")
        or sel.startswith(".message")
        or sel.startswith(".expand-hint")
    ):
        return "findings.css"

    if (
        sel.startswith(".detail-body")
        or sel.startswith(".section")
        or sel.startswith(".desc")
        or sel.startswith(".rule-")
        or sel.startswith(".expl-")
    ):
        return "rule_explanation.css"

    if (
        sel.startswith(".fix")
        or sel.startswith(".action")
        or sel.startswith(".fixes")
        or sel.startswith(".actions")
    ):
        return "fixes.css"

    if (
        sel.startswith(".code ")
        or sel == ".code"
        or sel.startswith(".code-wrap")
    ):
        return "code.css"

    if sel.startswith(".codehilite"):
        return "pygments_overrides.css"

    if (
        sel.startswith(".group")
        or sel.startswith(".category")
        or sel.startswith(".file")
        or sel.startswith(".rule-")
        or sel.startswith(".snippet-marker")
        or sel.startswith(".line-range")
    ):
        return "groups.css"

    if sel.startswith(".code.diff-preview"):
        return "diff.css"

    if (
        sel.startswith("summary")
        or sel.startswith("details")
        or sel.startswith(".nested-details")
    ):
        return "details.css"

    if (
        sel.startswith(".code-container")
        or sel.startswith(".copy-code-btn")
    ):
        return "copy_button.css"

    return "misc.css"


blocks = parse_blocks(css)

for block in blocks:
    STYLE_FILES[target_file(selector(block))].append(block)

for filename, file_blocks in STYLE_FILES.items():
    content = "\n\n".join(file_blocks).strip()
    if content:
        OUT_DIR.joinpath(filename).write_text(content + "\n", encoding="utf-8")
    else:
        path = OUT_DIR / filename
        if path.exists():
            path.unlink()

print("CSS split complete.")
for filename, file_blocks in STYLE_FILES.items():
    if file_blocks:
        print(f"{filename}: {len(file_blocks)} blocks")
