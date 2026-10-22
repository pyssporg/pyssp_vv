"""Judgment: turn measured numbers into a verdict with reasons.

Order matters. Preconditions and sufficiency are checked before the criterion,
because a criterion evaluated on an unfit comparison is worse than no verdict at
all.

The result is one of ``pass``, ``fail`` or ``invalid``. ``blocked`` (the run
could not produce metrics) and ``waived`` (a recorded disposition overrides a
failure) are applied by the caller, never guessed here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from pyssp_vv.judge.criteria import MetricView
from pyssp_vv.judge.verdict import Verdict
from pyssp_vv.policy import Policy


@dataclass(frozen=True)
class Reason:
    """A machine-readable explanation, with optional human detail."""

    code: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True)
class SignalJudgment:
    signal: str
    verdict: Verdict
    value: float
    limit: float
    reasons: tuple[Reason, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "verdict": self.verdict.value,
            "value": self.value,
            "limit": self.limit,
            "reasons": [reason.to_dict() for reason in self.reasons],
        }


@dataclass(frozen=True)
class Judgment:
    verdict: Verdict
    signals: tuple[SignalJudgment, ...] = ()
    reasons: tuple[Reason, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "reasons": [reason.to_dict() for reason in self.reasons],
            "signals": [item.to_dict() for item in self.signals],
        }


def _value_for(metric: MetricView, policy: Policy) -> float:
    return float(getattr(metric, policy.criterion.metric.value))


def _reference_peak(metric: MetricView) -> float:
    return max(abs(metric.reference_max), abs(metric.reference_min))


def judge_signal(metric: MetricView, policy: Policy) -> SignalJudgment:
    """Judge one signal against one policy."""
    reasons: list[Reason] = []
    sufficiency = policy.sufficiency

    undefined = tuple(getattr(metric, "undefined", ()))
    if "no-comparable-samples" in undefined:
        reasons.append(Reason("no-comparable-samples", metric.signal))

    if metric.coverage < sufficiency.min_coverage:
        reasons.append(
            Reason(
                "coverage-below-minimum",
                f"coverage={metric.coverage:.3f} < {sufficiency.min_coverage:.3f}",
            )
        )

    reference_range = metric.reference_max - metric.reference_min
    if not math.isfinite(reference_range) or reference_range <= sufficiency.degenerate_range:
        reasons.append(
            Reason(
                "degenerate-signal",
                f"reference range={reference_range:.6g} <= {sufficiency.degenerate_range:.6g}",
            )
        )

    if (
        sufficiency.reject_shift_at_boundary
        and policy.comparison.shift_samples > 0
        and abs(metric.shift_samples) >= policy.comparison.shift_samples
    ):
        reasons.append(
            Reason(
                "shift-at-boundary",
                f"best shift {metric.shift_samples} at search edge "
                f"±{policy.comparison.shift_samples}",
            )
        )

    value = _value_for(metric, policy)
    limit = policy.criterion.limit(_reference_peak(metric))

    blocking = [reason for reason in reasons if reason.code != "criterion-exceeded"]
    if blocking:
        return SignalJudgment(
            signal=metric.signal,
            verdict=Verdict.INVALID,
            value=value,
            limit=limit,
            reasons=tuple(reasons),
        )

    if not math.isfinite(value) or not math.isfinite(limit):
        reasons.append(Reason("non-finite-metric", f"value={value} limit={limit}"))
        return SignalJudgment(
            signal=metric.signal,
            verdict=Verdict.INVALID,
            value=value,
            limit=limit,
            reasons=tuple(reasons),
        )

    verdict = Verdict.PASS if value <= limit else Verdict.FAIL
    if verdict is Verdict.FAIL:
        reasons.append(
            Reason(
                "criterion-exceeded",
                f"{value:.6g} > {limit:.6g} ({policy.criterion.metric.value})",
            )
        )
    return SignalJudgment(
        signal=metric.signal,
        verdict=verdict,
        value=value,
        limit=limit,
        reasons=tuple(reasons),
    )


def judge(metrics: Sequence[MetricView], policy: Policy) -> Judgment:
    """Judge a set of measured signals.

    Aggregation is pessimistic: any ``invalid`` makes the whole judgment
    ``invalid``; otherwise any ``fail`` makes it ``fail``.
    """
    if not metrics:
        return Judgment(
            verdict=Verdict.INVALID,
            reasons=(Reason("no-signals", "nothing was measured"),),
        )

    signals = tuple(judge_signal(metric, policy) for metric in metrics)

    reasons: list[Reason] = []
    seen: set[tuple[str, str]] = set()
    for item in signals:
        for reason in item.reasons:
            key = (reason.code, reason.detail)
            if key not in seen:
                seen.add(key)
                reasons.append(reason)

    verdicts = {item.verdict for item in signals}
    if Verdict.INVALID in verdicts:
        verdict = Verdict.INVALID
    elif Verdict.FAIL in verdicts:
        verdict = Verdict.FAIL
    else:
        verdict = Verdict.PASS

    return Judgment(verdict=verdict, signals=signals, reasons=tuple(reasons))
