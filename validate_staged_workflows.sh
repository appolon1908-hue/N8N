#!/usr/bin/env bash
set -euo pipefail
workflow_dir="$(cd "$(dirname "$0")" && pwd)"
for file in "$workflow_dir"/*.json; do
  [ -f "$file" ] || continue
  docker run --rm -v "$file:/workflow.json:ro" node:22-alpine node -e '
const fs=require("fs"); const w=JSON.parse(fs.readFileSync("/workflow.json"));
if (w.active !== false) throw new Error(`${w.name}: active must be false`);
if (!Array.isArray(w.nodes) || !w.nodes.some(n=>n.type==="n8n-nodes-base.manualTrigger")) throw new Error(`${w.name}: manual trigger missing`);
for (const n of w.nodes) {
  const raw=JSON.stringify(n).toLowerCase();
  if (/password|secret|api[_-]?key|credential|external_dial|vicidial|odoo|n8n\.codestra/.test(raw)) throw new Error(`${w.name}: forbidden integration or secret text in ${n.name}`);
  if (n.type === "n8n-nodes-base.httpRequest" && !(n.parameters?.options?.timeout >= 1000)) throw new Error(`${w.name}: HTTP timeout missing`);
}
console.log(`${w.name}: valid, inactive, manual-only, no credentials/live targets`);'
done
curl -fsS http://middleware:8095/readyz >/dev/null 2>&1 || curl -fsS https://api.codestra.agency/healthz >/dev/null
echo 'staged workflow validation passed; no workflow was imported, activated, or executed'
