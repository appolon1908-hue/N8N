# Codestra n8n Automation — Sprint 1

This repository contains 12 deterministic, inactive n8n 2.30.8 workflows: five reusable sub-workflows, one event router, five TEST_SYN business workflows, and one error/dead-letter workflow. Every HTTP request targets `http://middleware:8095`; no workflow connects to Odoo, VICIdial, Asterisk, a database, or a delivery provider.

Generate artifacts with `python3 scripts/build_sprint1_artifacts.py`. Validate with the scripts under `scripts/`. The isolated stack in `/opt/codestra/n8n-test` aliases the mock service as `middleware` on an internal-only Docker network.

Live import is permitted only after every isolated gate passes. Imported workflows must remain `active=false`; no trigger may be activated or executed during Sprint 1.
