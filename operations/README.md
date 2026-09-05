# Operations tooling

`runtime_path_audit.py` performs read-only discovery of:

- host identity, OS/kernel summary, and a non-reversible machine-id fingerprint prefix;
- relevant Docker container names, configured images, local image repo digests, safe Compose/OCI labels, mounts, networks, exposed container-port keys, health, configured user, read-only-rootfs state, capability drops, security options, and restart policy;
- candidate Compose file paths under `/root`, `/opt`, `/srv`, and `/etc/codestra`;
- candidate n8n directories plus owner IDs and permission modes, without reading file contents.

It deliberately excludes container environment variables, secret contents, database queries, workflow data, logs, and customer information. It does not restart, exec into, update, or otherwise mutate a container.

```bash
python3 operations/runtime_path_audit.py
```

Review the JSON before storing it as evidence. Remove unrelated internal paths, hash the sanitized artifact, and attach only the digest and approved evidence location to the runtime-verification pull request. The audit cannot determine licensed n8n features by itself; edition and endpoint-binding support require a separate read-only verification.

## Recovery authority

`backup/n8n-recovery-backup.sh` captures the production and staging databases,
workflow exports, encrypted credential authority, persistent n8n data, runtime
configuration, and immutable release identities. All plaintext work must be on
a verified tmpfs path. The encrypted recovery directory is published under a
non-blocking lock only after its signed manifest, files, and parent directory
are synchronized. `backup/check-n8n-backup-freshness.sh` verifies the pinned
signing identity and binds `LAST_SUCCESS` to signed status metadata.

`backup/verify-n8n-recovery.sh` is destructive only to two explicitly
authorized, initially empty, isolated restore databases. It rejects credentials
and endpoint overrides in database URLs, validates both encrypted and plaintext
checksums, safely inspects nested archives, restores both databases, verifies
the required n8n tables, and atomically publishes checksum-bound evidence.
`backup/check-n8n-recovery-freshness.sh` rejects incomplete, tampered, stale,
or future-dated results and binds the marker to the verified result timestamp.
Restore plaintext is confined to a separately verified tmpfs work root, and the
selected release SHA plus production/staging image digests must match exactly.
Source validation does not prove a live recovery test.

`backup/codestra-n8n-database-certify` is the bounded operator entrypoint for
that live evidence. It accepts only the literal `certify` action, loads only
the fixed root-owned configuration, verifies the latest signed backup, restores
only when the latest backup lacks matching isolated evidence, and then requires
fresh checksum-bound evidence for the same backup stamp. Install the companion
`sudoers/codestra-n8n-database-certify` policy only after `visudo -cf` passes.
The delegated identity receives no caller-controlled path, environment, shell,
live database target, workflow activation, or service-management authority.

Before installing or restarting the backup unit, the reviewed rollout must
merge the non-secret names from
`backup/database-certification.env.example` into the existing root-owned
`/etc/codestra/backup/database-certification.env`. Operators must replace every
placeholder with the approved signing fingerprint, exact release SHA, and exact
production/staging image digests, validate the file without printing its secret
values, and run the backup freshness preflight. The timer must not be enabled or
restarted until that preflight succeeds. `RuntimeDirectory=` creates the
private tmpfs work path on every boot before systemd applies `ReadWritePaths=`;
the backup script independently verifies that the path is tmpfs.
