# Codestra n8n staging

These JSON files are staging artifacts only. They are intentionally inactive and are not production workflows.

Run the read-only validator:

```sh
/opt/codestra/n8n-workflows/validate_staged_workflows.sh
```

The validator checks JSON syntax, manual-only triggers, inactive state, HTTP timeouts, and absence of credentials or live VICIdial/Odoo/n8n targets. It performs only a GET readiness check against middleware. It never imports, activates, executes, or POSTs a workflow.
