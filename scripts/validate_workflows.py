import json
import re
import sys
from pathlib import Path

mode = sys.argv[1] if len(sys.argv) > 1 else "integration"
root = Path(__file__).parents[1]
files = sorted((root / "workflows").glob("WF-*.json"))
assert len(files) == 9, f"expected 9 blueprint workflows, found {len(files)}"
for path in files:
    workflow = json.loads(path.read_text())
    assert workflow["active"] is False, f"{path.name}: active"
    assert workflow["meta"]["mode"] == mode or mode == "production-candidate", f"{path.name}: mode mismatch"
    assert workflow["meta"]["signature_verification"] is True
    assert workflow["meta"]["campaign_allowlist"] == "TEST_SYN"
    assert workflow["meta"]["environment"] == "test"
    assert workflow["meta"]["no_credentials"] is True
    assert workflow["meta"]["credential_reference"] == "codestraMiddlewareBearer"
    for node in workflow["nodes"]:
        if node["type"] == "n8n-nodes-base.httpRequest":
            reference = node.get("credentials", {}).get("httpHeaderAuth", {})
            assert reference.get("id") == "codestraMiddlewareBearer"
            assert reference.get("name") == "Codestra Middleware Bearer"
    raw = path.read_text().lower()
    assert not re.search(r"(odoo|vicidial|asterisk|postgres|redis|external_dial|executecommand|ssh|community)", raw)
    for node in workflow["nodes"]:
        if node["type"] == "n8n-nodes-base.httpRequest":
            assert node["parameters"].get("options", {}).get("timeout", 0) >= 1000
print(f"{mode} validation passed: {len(files)} inactive Middleware-only workflows")
