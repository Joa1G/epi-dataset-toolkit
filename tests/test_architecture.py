"""The rule the folder layout exists to express, checked instead of trusted.

core/ is what more than one tool needs; each tool folder depends only on
core/. Stated in a README that claim rots the first time someone reaches
sideways for a function. Here it fails the build instead.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "yolo_dataset_toolkit"
TOOLS = ("visualize", "validate", "dedup", "split", "convert")


def imported_packages(module: Path) -> set[str]:
    """Sibling packages this module reaches into, by relative import."""
    tree = ast.parse(module.read_text())
    reached = set()

    for node in ast.walk(tree):
        # level 2 is '..', which leaves this module's own folder.
        if isinstance(node, ast.ImportFrom) and node.level == 2 and node.module:
            reached.add(node.module.split(".")[0])

    return reached


@pytest.mark.parametrize("tool", TOOLS)
def test_a_tool_never_imports_another_tool(tool: str):
    for module in (PACKAGE / tool).glob("*.py"):
        outside = imported_packages(module)
        assert outside <= {"core"}, (
            f"{tool}/{module.name} importa {outside - {'core'}};"
            " o que duas ferramentas compartilham pertence a core/"
        )


def test_core_never_imports_a_tool():
    """The dependency points one way, or core/ is not core."""
    for module in (PACKAGE / "core").glob("*.py"):
        assert not imported_packages(module) & set(TOOLS)


def test_every_tool_folder_exposes_a_command():
    for tool in TOOLS:
        assert (PACKAGE / tool / "main.py").is_file()
