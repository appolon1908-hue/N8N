import json
from pathlib import Path

path = Path(__file__).parents[1] / "workflows/analytics/ANALYTICS-WORKFLOW-CATALOG.json"
catalog = json.loads(path.read_text())
assert catalog["kind"] == "capability_catalog"
assert catalog["implementationStatus"] == "planned"
expected = {f"ANL-{number:02d}" for number in range(1, 16)}
assert {workflow["id"] for workflow in catalog["workflows"]} == expected
assert catalog["environment"] == "staging"
assert catalog["active"] is False
assert catalog["externalDeliveryAllowed"] is False
assert catalog["authoritativeCalculationAllowed"] is False
assert catalog["vicidialDatabaseAccessAllowed"] is False
assert catalog["credentials"] == []
assert all(workflow["active"] is False for workflow in catalog["workflows"])
assert len(catalog["requiredControls"]) == 12
print("15 inactive planned analytics capabilities validated")
