import json
from pathlib import Path

path = Path(__file__).parents[1] / "workflows/ai/AI-WORKFLOW-CATALOG.json"
catalog = json.loads(path.read_text())
expected = {f"AI-{i:02d}" for i in range(1, 20)} | {"AI-99"}
actual = {row["id"] for row in catalog["workflows"]}
assert actual == expected
assert catalog["environment"] == "staging"
assert catalog["productionWriteGuard"] is True
assert catalog["credentials"] == []
assert all(row["active"] is False for row in catalog["workflows"])
assert len(catalog["requiredControls"]) == 16
print("20 AI workflows validated inactive with fail-closed catalog controls")
