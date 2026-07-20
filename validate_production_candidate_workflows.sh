#!/usr/bin/env bash
set -euo pipefail
python3 "$(dirname "$0")/scripts/validate_workflows.py" production-candidate
