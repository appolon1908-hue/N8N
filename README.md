# Codestra n8n Automation — Sprint 1

This repository contains deterministic, inactive n8n workflow definitions plus explicitly planned capability catalogs. Manifest-listed HTTP requests target the internal middleware boundary; workflows do not connect directly to Odoo, VICIdial, Asterisk, a database, or a delivery provider.

Generate artifacts with `python3 scripts/build_sprint1_artifacts.py`. Validate with the scripts under `scripts/`. The isolated stack in `/opt/codestra/n8n-test` aliases the mock service as `middleware` on an internal-only Docker network.

Live import is permitted only after every isolated gate passes. Imported workflows must remain `active=false`; no trigger may be activated or executed during Sprint 1.
