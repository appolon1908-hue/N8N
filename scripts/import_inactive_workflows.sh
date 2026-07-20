#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/scripts/verify_inactive_workflows.py"
python3 "$ROOT/scripts/scan_credential_placeholders.py"
echo 'Import intentionally disabled; workflows remain inactive pending approval.'
