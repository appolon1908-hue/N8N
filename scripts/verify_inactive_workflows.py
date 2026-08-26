import json
from pathlib import Path
root=Path(__file__).parents[1]
manifest=json.loads((root/"manifests/workflow-manifest.json").read_text())
expected={Path(item).name for item in manifest["legacy_workflows"]}
files=sorted((root/"workflows").glob("*.json")); assert {f.name for f in files}==expected
for f in files:
 w=json.loads(f.read_text()); assert w["active"] is False; assert w["meta"]["no_credentials"] is True
print(f"verified {len(files)} inactive workflows")
