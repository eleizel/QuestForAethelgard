"""Architectural boundary enforcement test suite.

Uses Python's AST module to inspect all non-UI domain modules in `src/` to ensure
they do not import GUI frameworks (`pyxel`, `pygame`) or the UI presentation layer (`src.ui`).
"""

import ast
import os
from pathlib import Path
import pytest

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"

# Directories that must remain strictly pure domain logic
DOMAIN_DIRS = ["entities", "data", "systems", "core"]

# Files that currently have known presentation/audio coupling and are scheduled for decoupling:
# - src/core/audio.py: Pyxel audio driver (Target: Phase 1 Adapter Pattern)
# - src/core/engine.py: Pyxel game loop runner (Target: Phase 6 Multi-Frontend Facade)
KNOWN_LEGACY_EXCEPTIONS = {
    "src/core/audio.py": "Scheduled for Phase 1 (AudioAdapter)",
    "src/core/engine.py": "Scheduled for Phase 6 (GameSession Facade / Engine decoupling)",
}

FORBIDDEN_MODULES = ("pyxel", "pygame", "src.ui")


def get_domain_python_files():
    """Discover all python source files across domain directories."""
    files = []
    for d in DOMAIN_DIRS:
        dir_path = SRC_ROOT / d
        if not dir_path.exists():
            continue
        for file_path in dir_path.rglob("*.py"):
            rel_path = file_path.relative_to(SRC_ROOT.parent).as_posix()
            files.append(rel_path)
    return sorted(files)


@pytest.mark.parametrize("file_rel_path", get_domain_python_files())
def test_no_forbidden_gui_imports(file_rel_path):
    """Enforce that domain files do not import GUI libraries or presentation modules."""
    full_path = SRC_ROOT.parent / file_rel_path

    if file_rel_path in KNOWN_LEGACY_EXCEPTIONS:
        pytest.xfail(f"Legacy exception: {KNOWN_LEGACY_EXCEPTIONS[file_rel_path]}")

    with open(full_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(full_path))

    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.append((node.module, node.lineno))

    violations = []
    for mod, lineno in imported_modules:
        for forbidden in FORBIDDEN_MODULES:
            if mod == forbidden or mod.startswith(f"{forbidden}."):
                violations.append((mod, lineno))

    assert not violations, (
        f"Architectural boundary violation in {file_rel_path}: "
        f"Domain core cannot import presentation/GUI layers: {violations}"
    )
