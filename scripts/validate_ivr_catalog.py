import json
from pathlib import Path

path = Path(__file__).parents[1] / "workflows/ivr/IVR-WORKFLOW-CATALOG.json"
catalog = json.loads(path.read_text())
expected = {f"IVR-{number:02d}" for number in range(1, 9)} | {"IVR-99"}
actual = {workflow["id"] for workflow in catalog["workflows"]}
assert actual == expected
assert catalog["environment"] == "staging"
assert catalog["active"] is False
assert catalog["externalDeliveryAllowed"] is False
assert catalog["vicidialControlAllowed"] is False
assert catalog["asteriskControlAllowed"] is False
assert catalog["credentials"] == []
assert all(value is True for value in catalog["requirements"].values())
assert all(workflow["active"] is False for workflow in catalog["workflows"])
print("9 inactive IVR staging workflows validated")
