#!/usr/bin/env python3
"""Run the N0 workflow inventory gate without third-party dependencies."""

from __future__ import annotations

from collections import Counter

from workflow_inventory import (
    ROOT,
    executable_workflow_files,
    inventory_markdown,
    pack_declarations,
)


def main() -> int:
    declarations = pack_declarations()
    errors: list[str] = []
    if len(declarations) != 65:
        errors.append(f"declared workflow count is {len(declarations)}, expected 65")

    declared_paths = [declaration.expected_path for declaration in declarations]
    counts = Counter(declared_paths)
    for workflow_file in executable_workflow_files():
        if counts[workflow_file] != 1:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
