#!/usr/bin/env bash
set -euo pipefail
python3 "$(dirname "$0")/workflow_validator.py" manifest
