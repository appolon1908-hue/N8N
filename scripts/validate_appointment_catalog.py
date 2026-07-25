import json
from pathlib import Path
p = Path(__file__).parents[1] / "workflows/appointments/APPT-WORKFLOW-CATALOG.json"
c = json.loads(p.read_text())
assert {x["id"] for x in c["workflows"]} == {f"APPT-{i:02d}" for i in range(1,8)} | {"APPT-99"}
assert all(not x["active"] for x in c["workflows"])
assert not c["externalDeliveryAllowed"] and not c["vicidialControlAllowed"]
assert c["credentials"] == []
print("8 appointment workflows validated inactive without telephony control")
