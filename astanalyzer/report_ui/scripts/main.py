from .state import build_script_state
from .normalise import build_script_data_normalisation
from .formatters import build_script_formatters
from .fixes import build_script_fix_helpers
from .finding_card import build_script_finding_card
from .grouping import build_script_grouping
from .rendering import build_script_rendering
from .io import build_script_io
from .events import build_script_events


def build_report_script(safe_json: str) -> str:
    return f"""
<script id="report-data" type="application/json">{safe_json}</script>
<script>
{build_script_state()}
{build_script_data_normalisation()}
{build_script_formatters()}
{build_script_fix_helpers()}
{build_script_finding_card()}
{build_script_grouping()}
{build_script_rendering()}
{build_script_io()}
{build_script_events()}
</script>
"""