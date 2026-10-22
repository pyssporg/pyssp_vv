"""Fingerprint of the environment that produced evidence.

Versions matter: a verdict produced by one engine build is not the same claim as
one produced by another. Names that are not installed are recorded as absent
rather than omitted, so "same version" and "not checked" stay distinguishable.
"""

from __future__ import annotations

import platform
import sys
from importlib import metadata
from typing import Iterable

DEFAULT_DISTRIBUTIONS = (
    "pyssp-vv",
    "pyssp-standard",
    "pyssp-simulate",
    "pyssp-workflow",
    "fmpy",
    "OMSimulator",
    "ssp4sim",
)


def fingerprint(distributions: Iterable[str] | None = None) -> dict[str, object]:
    """Return a JSON-able description of the running environment."""
    names = tuple(distributions if distributions is not None else DEFAULT_DISTRIBUTIONS)
    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "executable": sys.executable,
        "distributions": versions,
    }
