#!/usr/bin/env python3
"""Add the reviewed middleware credential reference to internal HTTP nodes."""

import json
from pathlib import Path

root = Path(__file__).parents[1] / "workflows"
changed = 0
for path in sorted(root.rglob("*.json")):
    workflow = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(workflow, dict) or not isinstance(workflow.get("nodes"), list):
        continue
    dirty = False
    for node in workflow["nodes"]:
        if node.get("type") != "n8n-nodes-base.httpRequest":
            continue
        url = str(node.get("parameters", {}).get("url", ""))
        if not (
            url.startswith("http://middleware:8095/")
            or url.startswith("={{$env.MIDDLEWARE_INTERNAL_URL}}")
        ):
            continue
        credentials = node.setdefault("credentials", {})
        if "httpHeaderAuth" not in credentials:
            credentials["httpHeaderAuth"] = {
                "id": "codestraMiddlewareBearer",
                "name": "Codestra Middleware Bearer",
            }
            dirty = True
    if dirty:
        path.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed += 1
print(f"credential references added to {changed} workflow files")
