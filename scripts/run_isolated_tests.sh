#!/usr/bin/env bash
set -euo pipefail
umask 077

runtime_dir=$(mktemp -d "${TMPDIR:-/tmp}/codestra-n8n-test.XXXXXX")
chmod 700 "$runtime_dir"
secret_file="$runtime_dir/mock-hmac-secret"
encryption_file="$runtime_dir/n8n-encryption-secret"
import_dir="$runtime_dir/import"
project="codestra_n8n_${BASHPID}"
cleanup() {
  rc=$?
  set +e
  if [ "$rc" -ne 0 ]; then
    docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml ps || true
    docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml logs --tail=80 n8n-test mock-middleware 2>&1 | sed -E 's/(password|secret|token|authorization)([=: ]+)[^ ]+/\1\2[REDACTED]/Ig' || true
  fi
  docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml down -v --remove-orphans >/dev/null 2>&1 || true
  rm -f "$secret_file" "$encryption_file"
  rm -rf "$import_dir"
  rmdir "$runtime_dir" 2>/dev/null || true
  trap - EXIT
  exit "$rc"
}
trap cleanup EXIT

openssl rand -hex 32 | tr -d '\n' > "$secret_file"
openssl rand -hex 32 | tr -d '\n' > "$encryption_file"
chmod 600 "$secret_file" "$encryption_file"
export MOCK_SECRET_FILE="$secret_file"
export N8N_ENCRYPTION_FILE="$encryption_file"
mkdir "$import_dir"
cp /opt/codestra/n8n-workflows/workflows/WF-*.json "$import_dir/"
chmod 755 "$import_dir"
chmod 644 "$import_dir"/*.json
export N8N_WORKFLOW_IMPORT_DIR="$import_dir"
export COMPOSE_PROJECT_NAME="$project"

echo "Starting isolated n8n test stack"
docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml up -d --build mock-middleware
docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml run --rm --no-deps n8n-test \
  import:workflow --separate --input=/workflows/import
docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml up -d n8n-test
healthy=false
for _ in $(seq 1 30); do
  if [ "$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "${project}-n8n-test-1")" = healthy ]; then
    healthy=true
    break
  fi
  sleep 2
done
if [ "$healthy" != true ]; then
  echo "n8n did not become healthy" >&2
  exit 1
fi

docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml exec -T n8n-test sh -lc \
  'rm -rf /tmp/gate5-export && mkdir /tmp/gate5-export && n8n export:workflow --all --separate --output=/tmp/gate5-export >/dev/null && node -e '\''const fs=require("fs"),p="/tmp/gate5-export";const f=fs.readdirSync(p).filter(x=>x.endsWith(".json"));if(f.length!==9)throw Error(`expected 9 workflows, got ${f.length}`);for(const x of f){if(JSON.parse(fs.readFileSync(`${p}/${x}`)).active!==false)throw Error(`${x} active`)}console.log("DISABLED_IMPORTS=9")'\'''

docker run --rm --network "${project}_test_backend" -e MOCK_URL=http://middleware:8096 \
  -e MOCK_SECRET_FILE=/run/mock-hmac -v /opt/codestra/n8n-workflows:/workflows:ro \
  -v "$secret_file":/run/mock-hmac:ro python:3.12.8-slim \
  python /workflows/scripts/run_mock_tests.py

docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml stop mock-middleware >/dev/null
if docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml exec -T n8n-test wget -qO- --timeout=2 http://middleware:8096/test/evidence >/dev/null 2>&1; then
  echo "dependency outage was not isolated" >&2; exit 1
fi
echo "DEPENDENCY_OUTAGE=PASS"
docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml start mock-middleware >/dev/null
docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml restart n8n-test >/dev/null
healthy=false
for _ in $(seq 1 30); do
  if [ "$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "${project}-n8n-test-1")" = healthy ]; then
    healthy=true
    break
  fi
  sleep 2
done
if [ "$healthy" != true ]; then
  echo "n8n did not recover after restart" >&2
  exit 1
fi
docker compose --project-name "$project" --file /opt/codestra/n8n-test/compose.yaml exec -T n8n-test sh -lc \
  'rm -rf /tmp/gate5-restart && mkdir /tmp/gate5-restart && n8n export:workflow --all --separate --output=/tmp/gate5-restart >/dev/null && test "$(find /tmp/gate5-restart -name "*.json" | wc -l)" -eq 9'
echo "RESTART_RECOVERY=PASS"
echo "isolated n8n test cleanup passed"
