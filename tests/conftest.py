"""One level marker per test file, applied at collection time.

The level is a property of the file, not of individual tests, so it is applied
here once instead of repeating ``@pytest.mark.level_*`` on every function.
``tests/test_layering.py`` asserts the invariant: every collected test carries
exactly one of these markers.
"""

from __future__ import annotations

import pytest

LEVEL_BY_FILE = {
    "test_layering.py": "level_static",
    "test_measure.py": "level_unit",
    "test_judge.py": "level_unit",
    "test_policy.py": "level_unit",
    "test_evidence.py": "level_component",
    "test_figures.py": "level_component",
    "test_contracts.py": "level_contract",
}


def pytest_collection_modifyitems(items):
    for item in items:
        level = LEVEL_BY_FILE.get(item.path.name)
        if level is not None:
            item.add_marker(getattr(pytest.mark, level))
