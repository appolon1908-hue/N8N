#!/usr/bin/env python3
"""Regenerate docs/WORKFLOW_INVENTORY.md."""

from __future__ import annotations

from pathlib import Path

try:
    from .workflow_inventory import ROOT, inventory_markdown
except ImportError:
    from workflow_inventory import ROOT, inventory_markdown  # type: ignore


def main() -> int:
    target = ROOT / "docs" / "WORKFLOW_INVENTORY.md"
    target.write_text(inventory_markdown(), encoding="utf-8", newline="\n")
    print(f"WROTE={target.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
