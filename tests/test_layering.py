"""Import-graph rules.

`policy`, `judge`, and `evidence` are the contracts and must stay
standard-library only. `measure` may use numpy. Nothing in this package may
depend on another pyssp project.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "pyssp_vv"

STDLIB_ONLY = ("policy", "judge", "evidence")
MEASURE = "measure"
MEASURE_ALLOWED = {"numpy"}
FORBIDDEN_PREFIXES = (
    "pyssp_standard",
    "pyssp_simulate",
    "pyssp_sysml2",
    "pyssp_workflow",
    "sequence_extensions",
)


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(["pyssp_vv", *parts]) if parts else "pyssp_vv"


def _layer(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else ""


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
    return names


def _walk():
    for path in sorted(SRC.rglob("*.py")):
        yield path, _module_name(path), _imports(path)


def test_contract_layers_are_standard_library_only():
    allowed = set(sys.stdlib_module_names) | {"__future__"}
    violations = [
        f"{module} imports {name}"
        for _path, module, imports in _walk()
        if _layer(module) in STDLIB_ONLY
        for name in imports
        if name.split(".")[0] not in allowed and name.split(".")[0] != "pyssp_vv"
    ]
    assert not violations, "a contract layer leaked a dependency:\n" + "\n".join(violations)


def test_measure_uses_only_numpy_beyond_the_contracts():
    allowed = set(sys.stdlib_module_names) | {"__future__", "_pytest"} | MEASURE_ALLOWED
    violations = [
        f"{module} imports {name}"
        for _path, module, imports in _walk()
        if _layer(module) == MEASURE
        for name in imports
        if name.split(".")[0] not in allowed and name.split(".")[0] != "pyssp_vv"
    ]
    assert not violations, "measure gained an unexpected dependency:\n" + "\n".join(violations)


def test_no_pyssp_project_is_imported():
    violations = [
        f"{module} imports {name}"
        for _path, module, imports in _walk()
        for name in imports
        if name.startswith(FORBIDDEN_PREFIXES)
    ]
    assert not violations, (
        "pyssp_vv must not depend on another pyssp project:\n" + "\n".join(violations)
    )


def test_judge_does_not_import_measure():
    violations = [
        f"{module} imports {name}"
        for _path, module, imports in _walk()
        if _layer(module) == "judge"
        for name in imports
        if name.startswith("pyssp_vv.measure")
    ]
    assert not violations, (
        "judgment must consume metric tables, not trajectories:\n" + "\n".join(violations)
    )
