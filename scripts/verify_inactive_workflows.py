import json,re
from pathlib import Path
files=sorted((Path(__file__).parents[1]/"workflows").glob("*.json")); assert len(files)==18
for f in files:
 w=json.loads(f.read_text()); assert w["active"] is False; assert w["meta"]["no_credentials"] is True; raw=f.read_text().replace('no_credentials',''); assert not re.search(r'password|secret|api[_-]?key|authorization',raw,re.I)
print(f"verified {len(files)} inactive workflows")
