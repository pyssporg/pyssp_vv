"""Static policy: tests never write into the checkout.

Inline minimal CSVs and XML are deliberate unit inputs; anything reused by two
tests must become a ``tests/fixtures/<case>/`` directory with ``input.<ext>``
and ``case.md``. Every write in this suite goes to ``tmp_path``. The check
parses the test modules and fails on a literal-path write, on a write in a
function with no ``tmp_path`` argument, and on any ``tmp_path``-free write that
is not listed below with a reason.
"""

from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent

#: Call forms that create or modify a file.
WRITE_METHODS = {"write_text", "write_bytes", "write_parquet"}

#: Functions that write to a caller-supplied path and therefore carry no
#: ``tmp_path``; each caller in the suite passes a ``tmp_path`` child.
TMP_PATH_FREE_WRITES: dict[str, str] = {}

#: Parameters that make a write site acceptable as a ``tmp_path`` write.
TMP_PATH_PARAMETERS = {"tmp_path", "tmp_path_factory"}


def _is_literal_path(node: ast.expr) -> bool:
    """True when the expression has a string literal as its base path."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in {"Path", "PurePath"}:
            return bool(node.args) and _is_literal_path(node.args[0])
    if isinstance(node, ast.BinOp):
        return _is_literal_path(node.left)
    return False


def _write_sites(tree: ast.AST) -> list[tuple[int, ast.expr]]:
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in WRITE_METHODS:
            sites.append((node.lineno, node.func.value))
        elif (
            isinstance(node.func, ast.Name)
            and node.func.id == "open"
            and len(node.args) > 1
        ):
            mode = node.args[1]
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
                if {"w", "a", "x", "+"} & set(mode.value):
                    sites.append((node.lineno, node.args[0]))
    return sites


def _enclosing_function(tree: ast.AST, lineno: int) -> ast.FunctionDef | None:
    found = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.lineno <= lineno <= (node.end_lineno or node.lineno)
    ]
    return min(found, key=lambda node: lineno - node.lineno) if found else None


def test_writes_go_to_tmp_path_or_a_listed_helper():
    offenders = []
    for path in sorted(TESTS.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for lineno, target in _write_sites(tree):
            function = _enclosing_function(tree, lineno)
            name = function.name if function else "<module>"
            parameters = {argument.arg for argument in function.args.args} if function else set()
            location = f"{path.name}:{lineno} ({name})"
            if _is_literal_path(target):
                offenders.append(f"{location} writes a literal path")
            elif not parameters & TMP_PATH_PARAMETERS and name not in TMP_PATH_FREE_WRITES:
                offenders.append(f"{location} writes without tmp_path")

    assert offenders == [], "\n".join(offenders)


def test_every_tmp_path_free_write_is_listed_with_a_reason():
    defined = set()
    for path in TESTS.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined |= {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }

    missing = sorted(set(TMP_PATH_FREE_WRITES) - defined)

    assert missing == [], f"allowlisted helpers that no longer exist: {missing}"


def test_no_test_reads_the_working_directory():
    offenders = []
    for path in sorted(TESTS.glob("test_*.py")):
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            if "Path.cwd()" in line or "os.getcwd()" in line:
                offenders.append(f"{path.name}:{number}")

    assert offenders == [], offenders
