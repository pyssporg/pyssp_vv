"""The evidence bundle: the artifact a verification claim is made of.

A bundle names its inputs by digest, records the environment, and lists one
verdict per oracle. It contains no trajectories and no live objects, so it is
safe to archive, diff, and hand to a reviewer.

Paths stored in a bundle are relative to the bundle file.
:meth:`InputRef.from_file` performs that relativisation; nothing else should
invent paths.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from pyssp_vv.evidence.hashing import digest_path
from pyssp_vv.judge.verdict import Verdict
from pyssp_vv.version import SCHEMA_VERSION


@dataclass(frozen=True)
class InputRef:
    """One input artifact, addressed relative to the bundle."""

    role: str
    path: str
    sha256: str

    @classmethod
    def from_file(cls, role: str, path: Path, *, base_dir: Path) -> "InputRef":
        resolved = Path(path).resolve()
        try:
            relative = resolved.relative_to(Path(base_dir).resolve()).as_posix()
        except ValueError:
            relative = resolved.as_posix()
        return cls(role=role, path=relative, sha256=digest_path(resolved))

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "path": self.path, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InputRef":
        return cls(role=str(data["role"]), path=str(data["path"]), sha256=str(data["sha256"]))


@dataclass(frozen=True)
class VerdictRecord:
    """The outcome of one oracle evaluation."""

    oracle_id: str
    kind: str
    verdict: Verdict
    metrics: Mapping[str, float] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "oracle_id": self.oracle_id,
            "kind": self.kind,
            "verdict": Verdict(self.verdict).value,
            "metrics": {key: float(value) for key, value in self.metrics.items()},
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VerdictRecord":
        return cls(
            oracle_id=str(data["oracle_id"]),
            kind=str(data["kind"]),
            verdict=Verdict(data["verdict"]),
            metrics={key: float(value) for key, value in dict(data.get("metrics", {})).items()},
            reasons=tuple(data.get("reasons", ())),
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EvidenceBundle:
    """One assessment's worth of durable evidence."""

    assessment_id: str
    inputs: tuple[InputRef, ...]
    verdicts: tuple[VerdictRecord, ...]
    environment: Mapping[str, Any]
    created: str = field(default_factory=_utc_now)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "assessment_id": self.assessment_id,
            "created": self.created,
            "environment": dict(self.environment),
            "inputs": [item.to_dict() for item in self.inputs],
            "verdicts": [item.to_dict() for item in self.verdicts],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceBundle":
        return cls(
            assessment_id=str(data["assessment_id"]),
            inputs=tuple(InputRef.from_dict(item) for item in data.get("inputs", ())),
            verdicts=tuple(VerdictRecord.from_dict(item) for item in data.get("verdicts", ())),
            environment=dict(data.get("environment", {})),
            created=str(data["created"]),
            schema_version=str(data.get("schema_version", SCHEMA_VERSION)),
        )

    def write(self, path: Path) -> Path:
        """Write the bundle as JSON and return its absolute path."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(self.to_dict(), indent=2, sort_keys=True)
        target.write_text(text + "\n", encoding="utf-8")
        return target.resolve()

    @classmethod
    def read(cls, path: Path) -> "EvidenceBundle":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
