from importlib.resources import files

def load_js(name: str) -> str:
    return files("astanalyzer.report_ui.scripts").joinpath(name).read_text("utf-8")


def build_report_script(safe_json: str) -> str:
    parts = [
        "state.js",
        "normalise.js",
        "formatters.js",
        "fixes.js",
        "finding_card.js",
        "grouping.js",
        "rendering.js",
        "io.js",
        "events.js",
    ]

    js = "\n".join(load_js(p) for p in parts)

    return f"""
<script id="report-data" type="application/json">{safe_json}</script>
<script>
{js}
</script>
"""
