import json
from pathlib import Path

path = Path(__file__).parents[1] / "workflows/reporting/RPT-WORKFLOW-CATALOG.json"
catalog = json.loads(path.read_text())
assert {x["id"] for x in catalog["workflows"]} == {f"RPT-{i:02d}" for i in range(1, 9)}
assert len(catalog["requiredControls"]) == 14
assert catalog["environment"] == "staging"
assert catalog["productionWriteGuard"] is True
assert catalog["externalDeliveryAllowed"] is False
assert catalog["credentials"] == []
assert all(x["active"] is False for x in catalog["workflows"])
print("8 reporting workflows validated inactive and external-delivery disabled")
