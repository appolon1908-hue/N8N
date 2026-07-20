# n8n workflow reconciliation

The manifest is authoritative for the 12 inactive foundation workflows.
The other 27 pre-existing JSON files were not deleted or overwritten; they
are explicitly listed as `legacy_workflows` in
`manifests/workflow-manifest.json` and are excluded from candidate validation.

Validation now passes for the 12 manifest-listed workflows:

- manifest/count: passed
- inactive TEST_SYN scope: passed
- forbidden-node scan: passed
- allowed-host scan: passed
- secret scan: passed
- JSON manifest parsing: passed

Dynamic context URLs are accepted only for the exact internal expression
`={{$json.context_url}}`; the workflow code constructs that value from the
fixed `http://middleware:8095/` host. Environment-based URLs are accepted only
through `MIDDLEWARE_INTERNAL_URL` and remain subject to deployment allowlists.

An ephemeral mock secret was generated in a mode-600 temporary file for the
isolated test attempt and removed afterward. It was never committed or
printed. The local mock-server test could not execute because sandbox network
binding is prohibited; no external network connection was attempted.
