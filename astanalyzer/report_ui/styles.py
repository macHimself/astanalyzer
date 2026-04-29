from importlib.resources import files


STYLE_FILES_BEFORE_PYGMENTS = [
    "base.css",
    "toolbar.css",
    "findings.css",
    "rule_explanation.css",
    "fixes.css",
    "code.css",
]

STYLE_FILES_AFTER_PYGMENTS = [
    "pygments_overrides.css",
    "groups.css",
    "diff.css",
    "details.css",
    "copy_button.css",
  #  "misc.css",
]


def load_css(name: str) -> str:
    return (
        files("astanalyzer.report_ui")
        .joinpath("styles", name)
        .read_text(encoding="utf-8")
    )


def build_report_styles(pygments_css: str) -> str:
    css = "\n\n".join([
        *(load_css(name) for name in STYLE_FILES_BEFORE_PYGMENTS),
        pygments_css,
        *(load_css(name) for name in STYLE_FILES_AFTER_PYGMENTS),
    ])

    return f"<style>\n{css}\n</style>"
