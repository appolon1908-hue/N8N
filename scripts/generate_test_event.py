import json
from datetime import datetime,timezone
from uuid import uuid4
print(json.dumps({"event_id":str(uuid4()),"correlation_id":str(uuid4()),"schema_version":"v1","occurred_at":datetime.now(timezone.utc).isoformat(),"source":"test-harness","idempotency_key":"test-"+str(uuid4()),"event_type":"TEST_EVENT","payload":{"test_mode":True},"metadata":{"suite":"synthetic"}}))
