# Codestra n8n Automation — Sprint 1

This repository is the governed source of truth for Codestra n8n workflows, middleware contracts, service integration manifests, automation designs, and deployment validation.

> **Safety state:** the live server is unchanged. Production deployment is prohibited until runtime paths, service ownership, secrets locations, network routes, and immutable image digests are verified and reviewed.

Development changes must be proposed through feature branches and pull requests. No workflow committed to this repository may be active by default or bypass the middleware control plane.

This repository contains deterministic, inactive n8n workflow definitions plus explicitly planned capability catalogs. Manifest-listed HTTP requests target the internal middleware boundary; workflows do not connect directly to Odoo, VICIdial, Asterisk, a database, or a delivery provider.

Generate artifacts with `python3 scripts/build_sprint1_artifacts.py`. Validate with the scripts under `scripts/`. The isolated stack in `/opt/codestra/n8n-test` aliases the mock service as `middleware` on an internal-only Docker network.

Live import is permitted only after every isolated gate passes. Imported workflows must remain `active=false`; no trigger may be activated or executed during Sprint 1.
