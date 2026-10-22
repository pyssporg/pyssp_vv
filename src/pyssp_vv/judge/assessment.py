"""Assessments: what is being claimed, and against which policy.

An assessment declares one independent factor, the factors held constant across
its levels, and the oracles that judge it. It is data: JSON round-trippable, no
callables, no open handles. Unknown keys are rejected so a typo fails loudly
instead of silently disabling a declaration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from pyssp_vv.judge.verdict import Verdict
from pyssp_vv.policy import Policy
from pyssp_vv.version import SCHEMA_VERSION


def _reject_unknown(data: Mapping[str, Any], allowed: set[str], where: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"Unknown {where} keys: {sorted(unknown)}")


@dataclass(frozen=True)
class Factor:
    """The single independent variable of an assessment."""

    name: str
    levels: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Factor name must not be empty")
        if not self.levels:
            raise ValueError("Factor must declare at least one level")
        if len(set(self.levels)) != len(self.levels):
            raise ValueError(f"Factor {self.name!r} has duplicate levels")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "levels": list(self.levels)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Factor":
        _reject_unknown(data, {"name", "levels"}, "factor")
        return cls(name=str(data["name"]), levels=tuple(data["levels"]))


@dataclass(frozen=True)
class OracleRef:
    """One named judgment, with the policy it applies."""

    oracle_id: str
    kind: str
    policy: Policy
    params: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "oracle_id": self.oracle_id,
            "kind": self.kind,
            "policy": self.policy.to_dict(),
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OracleRef":
        _reject_unknown(data, {"oracle_id", "kind", "policy", "params"}, "oracle")
        return cls(
            oracle_id=str(data["oracle_id"]),
            kind=str(data["kind"]),
            policy=Policy.from_dict(data["policy"]),
            params=dict(data.get("params", {})),
        )


@dataclass(frozen=True)
class Disposition:
    """A recorded decision to accept a known outcome.

    Valid only for a named assessment and oracle. It records who accepted it and
    when it must be revisited, so a waiver cannot become a permanent exemption.
    """

    assessment_id: str
    oracle_id: str
    verdict: Verdict
    reason: str
    owner: str
    expires: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "oracle_id": self.oracle_id,
            "verdict": Verdict(self.verdict).value,
            "reason": self.reason,
            "owner": self.owner,
            "expires": self.expires,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Disposition":
        _reject_unknown(
            data,
            {"assessment_id", "oracle_id", "verdict", "reason", "owner", "expires"},
            "disposition",
        )
        return cls(
            assessment_id=str(data["assessment_id"]),
            oracle_id=str(data["oracle_id"]),
            verdict=Verdict(data["verdict"]),
            reason=str(data["reason"]),
            owner=str(data["owner"]),
            expires=data.get("expires"),
        )


@dataclass(frozen=True)
class Assessment:
    """One controlled comparison: a factor, its held constants, and oracles."""

    assessment_id: str
    model: str
    case: str
    factor: Factor
    held: tuple[str, ...]
    oracles: tuple[OracleRef, ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.assessment_id:
            raise ValueError("assessment_id must not be empty")
        if not self.model or not self.case:
            raise ValueError("model and case must not be empty")
        if not self.oracles:
            raise ValueError("An assessment must declare at least one oracle")
        if self.factor.name in self.held:
            raise ValueError(
                f"{self.factor.name!r} is both the independent factor and a held "
                "factor; a comparison cannot vary and hold the same thing"
            )
        if len(set(self.held)) != len(self.held):
            raise ValueError("held factors must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "assessment_id": self.assessment_id,
            "model": self.model,
            "case": self.case,
            "factor": self.factor.to_dict(),
            "held": list(self.held),
            "oracles": [oracle.to_dict() for oracle in self.oracles],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Assessment":
        _reject_unknown(
            data,
            {"schema_version", "assessment_id", "model", "case", "factor", "held", "oracles"},
            "assessment",
        )
        return cls(
            assessment_id=str(data["assessment_id"]),
            model=str(data["model"]),
            case=str(data["case"]),
            factor=Factor.from_dict(data["factor"]),
            held=tuple(data["held"]),
            oracles=tuple(OracleRef.from_dict(item) for item in data["oracles"]),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )
