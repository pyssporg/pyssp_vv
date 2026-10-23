"""Import-graph rules.

`policy`, `judge`, and `evidence` are the contracts and must stay
standard-library only. `measure`'s module-level imports are numpy only;
matplotlib is allowed inside `render_figure`, never at module level. Nothing in
this package may depend on another pyssp project.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "pyssp_vv"

STDLIB_ONLY = ("policy", "judge", "evidence")
MEASURE = "measure"
MEASURE_ALLOWED = {"numpy"}
MEASURE_FUNCTION_LOCAL_ALLOWED = {"matplotlib"}
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


def _module_level_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
    return names


def _walk():
    for path in sorted(SRC.rglob("*.py")):
        yield path, _module_name(path), _imports(path)


def _run_python(code: str) -> None:
    """Run ``code`` in a fresh interpreter with ``src`` importable."""
    environment = dict(os.environ, PYTHONPATH=str(SRC.parent))
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr


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
    allowed = set(sys.stdlib_module_names) | {"__future__"} | MEASURE_ALLOWED
    violations = [
        f"{module} imports {name}"
        for path, module, _ in _walk()
        if _layer(module) == MEASURE
        for name in _module_level_imports(path)
        if name.split(".")[0] not in allowed and name.split(".")[0] != "pyssp_vv"
    ]
    assert not violations, (
        "measure gained an unexpected module-level dependency:\n" + "\n".join(violations)
    )


def test_measure_function_local_imports_stay_within_declared_extras():
    allowed = (
        set(sys.stdlib_module_names)
        | {"__future__", "_pytest"}
        | MEASURE_ALLOWED
        | MEASURE_FUNCTION_LOCAL_ALLOWED
    )
    violations = [
        f"{module} imports {name}"
        for _path, module, imports in _walk()
        if _layer(module) == MEASURE
        for name in imports
        if name.split(".")[0] not in allowed and name.split(".")[0] != "pyssp_vv"
    ]
    assert not violations, "measure gained an unexpected dependency:\n" + "\n".join(violations)


def test_importing_measure_does_not_load_matplotlib():
    _run_python(
        "import sys; import pyssp_vv.measure.figures; "
        "assert 'matplotlib' not in sys.modules"
    )


def test_importing_evidence_does_not_load_numpy_or_matplotlib():
    _run_python(
        "import sys; import pyssp_vv.evidence.metrics; "
        "assert 'numpy' not in sys.modules; "
        "assert 'matplotlib' not in sys.modules"
    )


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
