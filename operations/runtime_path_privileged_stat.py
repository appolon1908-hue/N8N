#!/usr/bin/env python3
"""Emit metadata only for the fixed root-readable paths required by N3."""

from __future__ import annotations

import datetime as dt
import json
import os
import socket
import stat
from pathlib import Path
from typing import Any, Iterable


ALLOWLIST = (
    Path("/root/codestra-production-completion"),
    Path("/opt/codestra/n8n-staging/compose.yaml"),
    Path("/opt/codestra/n8n-staging/compose.queue.override.yaml"),
    Path("/var/lib/docker/volumes/codestra_n8n_data/_data"),
    Path("/var/lib/docker/volumes/codestra-n8n-staging_n8n_data/_data"),
    Path("/var/lib/docker/volumes/codestra-n8n-staging_postgres_data/_data"),
    Path("/var/lib/docker/volumes/codestra-n8n-staging_queue_redis_data/_data"),
    Path("/etc/codestra/secrets/codestra-compose"),
    Path("/etc/codestra/secrets/n8n-staging"),
    Path("/opt/codestra/middleware/deploy/internal-n8n-private/Caddyfile"),
    Path("/opt/codestra/backups/n8n-recovery"),
    Path("/opt/codestra/backups/n8n"),
)


def metadata(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        row: dict[str, Any] = {"path": str(path)}
        try:
            details = path.lstat()
        except OSError as exc:
            row["error"] = type(exc).__name__
        else:
            row.update(
                {
                    "type": "symlink" if stat.S_ISLNK(details.st_mode) else (
                        "directory" if stat.S_ISDIR(details.st_mode) else "file"
                    ),
                    "uid": details.st_uid,
                    "gid": details.st_gid,
                    "mode": f"{stat.S_IMODE(details.st_mode):04o}",
                    "device": details.st_dev,
                    "inode": details.st_ino,
                }
            )
        rows.append(row)
    return rows


def main() -> int:
    if os.geteuid() != 0:
        print("ERROR=must run as root", flush=True)
        return 77
    report = {
        "audit_version": "1.0",
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "policy": "FIXED_ALLOWLIST_METADATA_ONLY",
        "mutation_performed": False,
        "paths": metadata(ALLOWLIST),
        "excluded": [
            "file contents",
            "directory listings",
            "environment variables",
            "secret contents",
            "database queries",
            "workflow data",
            "container logs",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
