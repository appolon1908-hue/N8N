#!/usr/bin/env python3
"""Run the workflow-pack completeness gate without third-party dependencies."""

from __future__ import annotations

from collections import Counter

try:
    from .workflow_inventory import (
        ROOT,
        executable_workflow_files,
        inventory_markdown,
        pack_declarations,
    )
except ImportError:
    from workflow_inventory import (  # type: ignore
        ROOT,
        executable_workflow_files,
        inventory_markdown,
        pack_declarations,
    )


def main() -> int:
    declarations = pack_declarations()
    errors: list[str] = []
    if not declarations:
        errors.append("no workflow-pack declarations were found")

    workflow_ids = [declaration.workflow_id for declaration in declarations]
    workflow_id_counts = Counter(workflow_ids)
    for workflow_id, count in sorted(workflow_id_counts.items()):
        if count != 1:
            errors.append(f"workflow id {workflow_id} is declared {count} times")

    declared_paths = [declaration.expected_path for declaration in declarations]
    path_counts = Counter(declared_paths)
    for expected_path, count in sorted(path_counts.items(), key=lambda item: item[0].as_posix()):
        if count != 1:
            relative = expected_path.relative_to(ROOT).as_posix()
            errors.append(f"expected workflow path {relative} is declared {count} times")

    for workflow_file in executable_workflow_files():
        if path_counts[workflow_file] != 1:
            relative = workflow_file.relative_to(ROOT).as_posix()
            errors.append(f"{relative} must be declared exactly once")

    inventory = ROOT / "docs" / "WORKFLOW_INVENTORY.md"
    if inventory.read_text(encoding="utf-8") != inventory_markdown():
        errors.append("docs/WORKFLOW_INVENTORY.md is stale")

    missing = [declaration for declaration in declarations if not declaration.built]
    if errors:
        print("WORKFLOW_COMPLETENESS=FAIL")
        for error in errors:
            print(f"ERROR={error}")
        return 1

    print("WORKFLOW_COMPLETENESS=PASS")
    print(f"WORKFLOWS_DECLARED={len(declarations)}")
    print(f"WORKFLOWS_BUILT={len(declarations) - len(missing)}")
    print(f"EXPECTED_MISSING={len(missing)}")
    print("WORKFLOW_COUNT_SOURCE=automations/packs/*.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
