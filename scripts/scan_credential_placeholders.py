import json,re
from pathlib import Path
for f in (Path(__file__).parents[1]/"workflows").glob("*.json"):
 raw=f.read_text(); json.loads(raw); assert not re.search(r'(password|secret|api[_-]?key|authorization|credential)\s*[:=]',raw,re.I)
print("credential-placeholder scan passed")
