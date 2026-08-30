# Repository Profile — `N8N`

## Identity

- **Repository:** `appolon1908-hue/N8N`
- **Category:** Platform orchestration — workflows
- **Visibility:** `private`
- **Default branch:** `main`
- **Authority:** Primary n8n workflow and automation authority
- **Status:** Active orchestration repository; production workflows and external effects remain activation-gated.

## Purpose

Defines business and integration workflows, schedules, routing, transformations, and operational automation that call governed platform APIs.

## Owns

- n8n workflow definitions and workflow-family organization
- Automation sequencing, scheduling, transformations, and coordination
- Workflow fixtures, inactive templates, failure paths, and orchestration evidence

## Does not own

- Authoritative business state or correctness storage
- Direct provider or Odoo writes that bypass Middleware
- Secrets committed inside workflow exports

## Key integrations

- Middleware
- Odoo
- Product APIs and webhooks
- Email, SMS, voice, crawler, and provisioning systems through governed Middleware contracts

## Current priorities

1. Separate workflow families and service identities by business capability
2. Keep every privileged mutation behind Middleware
3. Add workflow tests, fixtures, replay safety, and failure/recovery evidence
4. Promote only reviewed inactive-to-active workflow changes

## Governance and safety

- Promotion model: `feature/docs/fix/security/upgrade -> development -> test -> staging -> production -> main`.
- Use pull requests and exact-head/merge-result validation; source merge never activates a workflow.
- Never commit credentials, execution data, customer payloads, database dumps, or secret-bearing workflow exports.
- Workflow activation, schedules, and live provider effects require separate protected approval.
- This document does not activate n8n workflows, write Odoo, call providers, or deploy n8n.

## Account-wide catalog

See `appolon1908-hue/documentaions/REPOSITORY_CATALOG.md`.
