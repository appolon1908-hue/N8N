#!/usr/bin/env python3
import json
from pathlib import Path

root = Path(__file__).parents[1]
main = json.loads(
    (root / "workflows/reconciliation/CdstCrmVicidialReconciliationV1.json").read_text()
)
failure = json.loads(
    (root / "workflows/reconciliation/CdstCrmVicidialReconciliationFailureV1.json").read_text()
)
assert main["active"] is False
assert failure["active"] is False
assert main["settings"]["errorWorkflow"] == failure["id"]
normalizer = next(node for node in main["nodes"] if node["id"] == "normalise")
code = normalizer["parameters"]["jsCode"]
assert "localeCompare" in code and "numeric:true" in code
for workflow in (main, failure):
    for node in workflow["nodes"]:
        if node["type"] == "n8n-nodes-base.httpRequest":
            credential = node.get("credentials", {}).get("httpHeaderAuth", {})
            assert credential.get("id") == "codestraMiddlewareBearer", node["name"]
release = next(node for node in failure["nodes"] if node["id"] == "release")
assert release["parameters"]["method"] == "POST"
assert release["parameters"]["url"].endswith("/fail-by-correlation")
assert failure["meta"]["releases_distributed_lock"] is True
print("inactive reconciliation ordering, authentication, and failure release validated")
