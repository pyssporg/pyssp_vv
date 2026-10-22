"""Evidence bundles: hash-addressed, relative paths, JSON-only."""

from __future__ import annotations

import pytest

from pyssp_vv.evidence import EvidenceBundle, InputRef, VerdictRecord
from pyssp_vv.evidence.hashing import digest_path
from pyssp_vv.judge import Verdict


def test_relative_path_and_digest(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = run_dir / "result.csv"
    result.write_text("time,y\n0,0\n1,1\n", encoding="utf-8")

    ref = InputRef.from_file("result", result, base_dir=run_dir)

    assert ref.path == "result.csv"
    assert ref.sha256.startswith("sha256:")
    assert ref.sha256 == digest_path(result)


def test_bundle_roundtrip(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    result = run_dir / "result.csv"
    result.write_text("time,y\n0,0\n", encoding="utf-8")

    bundle = EvidenceBundle(
        assessment_id="BouncingBall/baseline",
        inputs=(InputRef.from_file("result", result, base_dir=run_dir),),
        verdicts=(
            VerdictRecord(
                oracle_id="agreement",
                kind="cross_engine",
                verdict=Verdict.INVALID,
                metrics={"max_abs": 1.0},
                reasons=("coverage-below-minimum",),
            ),
        ),
        environment={"python": "3.10.12"},
        created="2026-10-22T00:00:00+00:00",
    )

    path = bundle.write(tmp_path / "out" / "evidence.json")

    assert path.is_absolute() and path.is_file()
    assert EvidenceBundle.read(path) == bundle


def test_directory_digest_tracks_content(tmp_path):
    tree = tmp_path / "ssp"
    (tree / "resources").mkdir(parents=True)
    (tree / "SystemStructure.ssd").write_text("<ssd/>", encoding="utf-8")
    before = digest_path(tree)

    (tree / "resources" / "model.fmu").write_bytes(b"fmu")
    assert digest_path(tree) != before


def test_non_json_metrics_fail_before_writing(tmp_path):
    bundle = EvidenceBundle(
        assessment_id="x/y",
        inputs=(),
        verdicts=(
            VerdictRecord(
                oracle_id="bad",
                kind="invariant",
                verdict=Verdict.FAIL,
                metrics={"value": object()},
            ),
        ),
        environment={},
        created="2026-10-22T00:00:00+00:00",
    )

    target = tmp_path / "evidence.json"
    with pytest.raises(TypeError):
        bundle.write(target)
    assert not target.exists()
