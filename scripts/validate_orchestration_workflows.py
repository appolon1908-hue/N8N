import json
from pathlib import Path

root = Path(__file__).parents[1] / "workflows" / "orchestration"
paths = sorted(root.glob("N8N-*.json"))
assert len(paths) == 6
for path in paths:
    workflow = json.loads(path.read_text())
    assert workflow["active"] is False
    assert workflow["meta"]["environment"] == "staging"
    assert workflow["meta"]["production_write_guard"] is True
    assert workflow["meta"]["no_credentials"] is True
    assert workflow["meta"]["business_unit_scope"] == "explicit"
    raw = path.read_text().lower()
    assert '"password":' not in raw
    assert "smtp" not in raw
    assert "executecommand" not in raw
    for node in workflow["nodes"]:
        if node["type"] == "n8n-nodes-base.httpRequest":
            assert node["parameters"]["options"]["timeout"] >= 1000
            assert node["credentials"]["httpHeaderAuth"]["id"] == "codestraMiddlewareBearer"
print("orchestration workflow validation passed: 6 inactive workflows")
