#!/usr/bin/env python3
import json
import re
from pathlib import Path

path = Path(__file__).parents[1] / "mappings/campaigns.staging.v1.json"
catalog = json.loads(path.read_text(encoding="utf-8"))
assert catalog["schema_version"] == 1
assert catalog["environment"] == "staging"
assert catalog["active"] is False
assert catalog["production_eligible"] is False
rows = catalog["mappings"]
assert rows
for field in ("mapping_uuid", "canonical_campaign_code", "vicidial_campaign_id", "n8n_scope"):
    values = [row[field] for row in rows]
    assert len(values) == len(set(values)), f"duplicate {field}"
for row in rows:
    assert row["schema_version"] == 1
    assert row["environment"] == "staging"
    assert row["desired_state"] == "inactive"
    assert row["production_eligible"] is False
    assert row["n8n_scope"] == (
        f"staging:{row['business_unit']}:{row['canonical_campaign_code']}"
    )
    assert re.fullmatch(r"[A-Z0-9-]+", row["canonical_campaign_code"])
    assert re.fullmatch(r"[A-Z0-9]{2,16}", row["vicidial_campaign_id"])
print(f"{len(rows)} unique inactive staging campaign mappings validated")
