# n8n automation foundation preflight

## Scope

This session is restricted to `/opt/codestra/n8n-workflows`,
`/opt/codestra/n8n-test`, and `/opt/codestra/backups/n8n-automation`.
Other Codestra repositories were not modified.

## Writer gate

No process directly modifying either n8n path was found. Two filesystem
snapshots taken approximately 15 seconds apart were identical.

## Existing work

The workflows repository is on `feature/n8n-automation-foundation` at
`4b091bf`. It contains substantial pre-existing untracked workflow, schema,
fixture, validator, script, template, and documentation work. These files
were preserved and were not overwritten.

The n8n test workspace is not a Git repository and contains an existing test
environment file, mock server, fixtures, and Compose file. It was preserved.

## Backup

`/opt/codestra/backups/n8n-automation/20260720-225831`

The repository archives and SHA-256 manifests validate successfully.

## Validation blockers

The current tree contains multiple workflow generations: the manifest expects
12 workflows, while `workflows/` contains 39 JSON files. The validators scan
all 39 and fail on the legacy/shared workflow
`workflows/shared/CdstFetchContextV1.json`, whose dynamic URL expression is
not accepted by the current allowed-host check.

The mock test runner also requires `MOCK_SECRET_FILE`, which was not supplied;
no secret was created or printed.

Because these conflicts predate this session and the instruction requires
preservation of unknown work, no workflow files were rewritten or deleted.
No live n8n import was attempted.
