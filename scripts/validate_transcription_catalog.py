import json
from pathlib import Path

path = Path(__file__).parents[1] / "workflows/transcription/TRANSCRIPTION-WORKFLOW-CATALOG.json"
catalog = json.loads(path.read_text())
assert catalog["kind"] == "capability_catalog"
assert catalog["implementationStatus"] == "planned"
assert {row["id"] for row in catalog["workflows"]} == {
    f"TRN-{number:02d}" for number in range(1, 13)
}
assert catalog["active"] is False
assert catalog["environment"] == "staging"
assert catalog["externalDeliveryAllowed"] is False
assert catalog["rawAudioInExecutionHistoryAllowed"] is False
assert catalog["historicalReprocessingAllowed"] is False
assert catalog["credentials"] == []
assert all(row["active"] is False for row in catalog["workflows"])
print("12 inactive planned transcription capabilities validated")
