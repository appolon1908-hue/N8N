# Operations tooling

`runtime_path_audit.py` performs read-only discovery of:

- host identity
- relevant Docker container names, images, safe Compose labels, mounts, networks, and exposed container port keys
- candidate Compose file paths under `/root`, `/opt`, `/srv`, and `/etc/codestra`
- candidate n8n directories without reading their contents

It deliberately excludes container environment variables, secret contents, database queries, workflow data, logs, and customer information.

```bash
python3 ops/runtime_path_audit.py
```

Review the JSON before storing it as evidence. Remove unrelated internal paths, hash the sanitized artifact, and attach only the digest and approved evidence location to the runtime-verification pull request.
