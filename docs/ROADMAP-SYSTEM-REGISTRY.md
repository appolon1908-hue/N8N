# Roadmap System Registry

Status: `SOURCE_ONLY`

This registry resolves the roadmap platform names used by the N8N X1 packs. All entries are design-only. n8n remains the orchestrator and calls Middleware only.

| System | Canonical Repo | n8n Role | Direct Access |
|---|---|---|---|
| Codestra Marketing | `appolon1908-hue/N8N` contract owner until product repo is assigned | campaign approval, provider sync request, attribution intake, reporting orchestration | prohibited |
| Codestra AI | `appolon1908-hue/N8N` contract owner until AI service repo is assigned | advisory copy/creative/extraction requests before human approval | prohibited |
| Codestra Communication | `appolon1908-hue/N8N` contract owner until communication service repo is assigned | nurture, qualification, reminder and follow-up orchestration | prohibited |
| Codestra Social | `appolon1908-hue/social.codestra.co` | content approval, scheduled publish request, engagement sync and result orchestration | prohibited |

## Social Naming Decision

Canonical name: `Codestra Social`

Canonical repository: `appolon1908-hue/social.codestra.co`

Historical or alias names:

- `postly.social`
- `Postiz`
- `Codesrea-Social-`

The X1 roadmap pack uses `codestra.social` for the pack name and `social.*` workflow ids. Existing `postly.social` pack declarations remain for the older CP-POSTLY lane until a later compatibility cleanup phase.

## Authority Boundaries

- Marketing owns campaign and attribution domain decisions, not n8n.
- AI output is advisory only and never authorizes spend, publishing or delivery.
- Communication owns consent decisions, not n8n.
- Social publishing is irreversible and requires approval before any publish command.
- Middleware remains the only write/command authority visible to n8n.
