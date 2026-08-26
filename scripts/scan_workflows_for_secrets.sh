#!/usr/bin/env bash
set -euo pipefail
! rg -n -i 'password\s*[=:]|secret\s*[=:]|api[_-]?key\s*[=:]|bearer [a-z0-9]' "$(dirname "$0")/../workflows"
echo 'secret scan passed'
