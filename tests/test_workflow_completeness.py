from __future__ import annotations

from collections import Counter

import pytest

from scripts.workflow_inventory import (
    ROOT,
    executable_workflow_files,
    inventory_markdown,
    pack_declarations,
)


DECLARATIONS = pack_declarations()


def _case(declaration):
    marks = []
    if not declaration.built:
        marks.append(
            pytest.mark.xfail(
                strict=True,
                reason=f"expected missing workflow: {declaration.relative_path}",
            )
        )
    return pytest.param(declaration, marks=marks, id=declaration.workflow_id)


@pytest.mark.parametrize("declaration", [_case(declaration) for declaration in DECLARATIONS])
def test_declared_pack_workflow_file_exists(declaration) -> None:
    assert declaration.expected_path.is_file(), declaration.relative_path


def test_every_executable_workflow_file_is_declared_once() -> None:
    declared_paths = [declaration.expected_path for declaration in DECLARATIONS]
    counts = Counter(declared_paths)
    for workflow_file in executable_workflow_files():
        assert counts[workflow_file] == 1, workflow_file.relative_to(ROOT).as_posix()


def test_pack_progress_metric_is_derived_from_unique_declarations() -> None:
    workflow_ids = [declaration.workflow_id for declaration in DECLARATIONS]
    expected_paths = [declaration.expected_path for declaration in DECLARATIONS]
    assert DECLARATIONS
    assert len(workflow_ids) == len(set(workflow_ids))
    assert len(expected_paths) == len(set(expected_paths))
    assert sum(1 for declaration in DECLARATIONS if declaration.built) <= len(DECLARATIONS)


def test_workflow_inventory_document_is_current() -> None:
    expected = inventory_markdown()
    actual = (ROOT / "docs" / "WORKFLOW_INVENTORY.md").read_text(encoding="utf-8")
    assert actual == expected


def test_validate_workflows_is_unconditional_in_ci() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "workflows:" in makefile
    assert "python3 scripts/validate_workflows.py workflows" in makefile
    assert "catalog-reconciliation:" in makefile
    assert "python3 scripts/validate_catalog_reconciliation.py" in makefile
    assert "make validate" in ci
