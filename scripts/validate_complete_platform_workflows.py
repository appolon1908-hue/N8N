import json
from pathlib import Path

root = Path(__file__).parents[1] / "workflows"
paths = (
    sorted(root.glob("[0-1][0-9]_*.json"))
    + sorted((root / "orchestration").glob("N8N-*.json"))
    + sorted((root / "platform").glob("*.json"))
)
expected = {
    *(f"{index:02d}" for index in range(1, 27)),
    "90", "91", "92", "93", "99",
}
observed = set()
for path in paths:
    workflow = json.loads(path.read_text())
    assert workflow["active"] is False, path
    prefix = workflow["name"].split()[0].split("_")[0].replace("N8N-", "")
    prefix = path.name[:2] if path.parent.name != "orchestration" else path.name[4:6]
    observed.add(prefix)
    raw = path.read_text().lower()
    assert '"active":true' not in raw.replace(" ", "")
    assert "smtp://" not in raw
assert expected <= observed, sorted(expected - observed)
print(f"complete platform workflow catalog passed: {len(expected)} required workflows inactive")
