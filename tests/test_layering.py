"""Import-graph rules.

`policy`, `judge`, and `evidence` are the contracts and must stay
standard-library only. `measure`'s module-level imports are numpy only;
matplotlib is allowed inside `render_figure`, never at module level. Nothing in
this package may depend on another pyssp project, and judgment must not reach
back into measurement.

Relative imports are resolved against the importing module's package before a
rule looks at them; ``from ..measure import Trajectory`` inside
``pyssp_vv.judge`` is the same edge as ``import pyssp_vv.measure``.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

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

LEVEL_MARKERS = (
    "level_static",
    "level_unit",
    "level_component",
    "level_contract",
    "level_integration",
    "level_system",
    "level_acceptance",
)


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(["pyssp_vv", *parts]) if parts else "pyssp_vv"


def _layer(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else ""


def _resolve_from(module: str, path: Path, node: ast.ImportFrom) -> str:
    """Absolute target of a relative ``from`` — the module's package plus level."""
    parts = module.split(".")
    if path.name != "__init__.py":
        parts = parts[:-1]
    ascends = node.level - 1
    if ascends > 0:
        parts = parts[:-ascends] if ascends <= len(parts) else []
    base = ".".join(parts)
    if node.module:
        return f"{base}.{node.module}" if base else node.module
    return base


def _targets(nodes: Iterable[ast.AST], path: Path, module: str) -> list[str]:
    names: list[str] = []
    for node in nodes:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from(module, path, node)
            if node.module is None:
                names.extend(f"{base}.{alias.name}" for alias in node.names)
            elif base:
                names.append(base)
    return names


def _imports(path: Path, module: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return _targets(ast.walk(tree), path, module)


def _module_level_imports(path: Path, module: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return _targets(tree.body, path, module)


def _walk():
    for path in sorted(SRC.rglob("*.py")):
        module = _module_name(path)
        yield path, module, _imports(path, module)


def _judge_importing_measure(entries: Sequence[tuple[Path, str, list[str]]]) -> list[str]:
    return [
        f"{module} imports {name}"
        for _path, module, imports in entries
        if _layer(module) == "judge"
        for name in imports
        if name == "pyssp_vv.measure" or name.startswith("pyssp_vv.measure.")
    ]


def _measure_importing_judge(entries: Sequence[tuple[Path, str, list[str]]]) -> list[str]:
    return [
        f"{module} imports {name}"
        for _path, module, imports in entries
        if _layer(module) == "measure"
        for name in imports
        if name == "pyssp_vv.judge" or name.startswith("pyssp_vv.judge.")
    ]


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


def _assert_import_is_clean(module: str, forbidden: Sequence[str]) -> None:
    checks = "; ".join(f"assert {name!r} not in sys.modules" for name in forbidden)
    _run_python(f"import sys; import {module}; {checks}")


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
        for name in _module_level_imports(path, module)
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


def test_contract_modules_do_not_load_numpy_or_matplotlib():
    for module in ("pyssp_vv.policy", "pyssp_vv.judge", "pyssp_vv.evidence.metrics"):
        _assert_import_is_clean(module, ("numpy", "matplotlib"))


def test_importing_measure_does_not_load_matplotlib():
    _assert_import_is_clean("pyssp_vv.measure", ("matplotlib",))


def test_importing_measure_loads_numpy_and_importing_the_contracts_does_not():
    # The probe above would also pass if measure silently lost its numeric
    # backend; pin the intended asymmetry.
    _run_python(
        "import sys; import pyssp_vv.policy; assert 'numpy' not in sys.modules; "
        "import pyssp_vv.measure; assert 'numpy' in sys.modules"
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
    violations = _judge_importing_measure(_walk())
    assert not violations, (
        "judgment must consume metric tables, not trajectories:\n" + "\n".join(violations)
    )


def test_measure_does_not_import_judge():
    violations = _measure_importing_judge(_walk())
    assert not violations, (
        "measurement must not decide acceptability:\n" + "\n".join(violations)
    )


def test_relative_import_bypass_is_closed(tmp_path):
    # The shape that used to slip through: `_imports` dropped every
    # `ImportFrom` with a level, so this edge was invisible to the rules.
    source = tmp_path / "judge" / "judge.py"
    source.parent.mkdir()
    source.write_text("from ..measure import Trajectory\n", encoding="utf-8")

    module = "pyssp_vv.judge.judge"
    entries = [(source, module, _imports(source, module))]

    assert entries[0][2] == ["pyssp_vv.measure"]
    assert _judge_importing_measure(entries)


def test_relative_imports_resolve_from_packages_and_parent_packages(tmp_path):
    cases = {
        "from .verdict import Verdict\n": (
            "mod.py",
            "pyssp_vv.evidence.bundle",
            "pyssp_vv.evidence.verdict",
        ),
        "from ..measure import Trajectory\n": (
            "mod.py",
            "pyssp_vv.judge.judge",
            "pyssp_vv.measure",
        ),
        "from . import judge\n": ("__init__.py", "pyssp_vv", "pyssp_vv.judge"),
    }
    for index, (text, (filename, module, expected)) in enumerate(cases.items()):
        path = tmp_path / f"case{index}" / filename
        path.parent.mkdir()
        path.write_text(text, encoding="utf-8")
        assert _imports(path, module) == [expected]


def test_every_collected_test_has_exactly_one_level_marker(request):
    problems = []
    for item in request.session.items:
        levels = [marker.name for marker in item.iter_markers() if marker.name in LEVEL_MARKERS]
        if len(levels) != 1:
            problems.append(f"{item.nodeid}: {levels}")
    assert not problems, (
        "every test must carry exactly one level marker (see tests/conftest.py):\n"
        + "\n".join(problems)
    )
