"""The verdict vocabulary.

``invalid`` is not a failure. It means the comparison was not legal: the
coverage was too low, the expectation was degenerate, or the declared shift
window was exhausted. Collapsing ``invalid`` into ``fail`` is what makes
uncontrolled comparisons look like model defects.

``blocked`` and ``waived`` are produced by the caller and by a disposition;
:func:`pyssp_vv.judge.judge.judge` only produces ``pass``, ``fail`` and
``invalid``.
"""

from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INVALID = "invalid"
    BLOCKED = "blocked"
    WAIVED = "waived"

    def __str__(self) -> str:
        return self.value
