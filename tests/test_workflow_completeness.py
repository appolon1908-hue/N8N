from __future__ import annotations

from collections import Counter
from pathlib import Path

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
                reason=f"N0 expected missing workflow: {declaration.relative_path}",
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


def test_pack_declaration_count_is_the_phase_progress_metric() -> None:
    assert len(DECLARATIONS) == 81
    assert sum(1 for declaration in DECLARATIONS if declaration.built) == 0


def test_workflow_inventory_document_is_current() -> None:
    expected = inventory_markdown()
    actual = (ROOT / "docs" / "WORKFLOW_INVENTORY.md").read_text(encoding="utf-8")
    assert actual == expected


def test_validate_workflows_is_unconditional_in_ci() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "workflows:" in makefile
    assert "python3 scripts/validate_workflows.py workflows" in makefile
    assert "make validate" in ci
