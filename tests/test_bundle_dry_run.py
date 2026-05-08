from __future__ import annotations

from pathlib import Path

import pytest

from planledger.bundle import apply_bundle, load_bundle
from planledger.errors import PlanledgerError
from planledger.storage import initialize_project, list_records

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "harness_bundle_v1.json"


@pytest.fixture
def workspace(tmp_path: Path):
    return initialize_project(tmp_path, "Dry Run Test")


def test_dry_run_validates_invalid_bundle(workspace):
    with pytest.raises(PlanledgerError, match="invalid_bundle"):
        apply_bundle(workspace, {"schema": "wrong"}, dry_run=True)


def test_dry_run_previews_without_writing(workspace):
    bundle = load_bundle(FIXTURE)
    result = apply_bundle(workspace, bundle, dry_run=True)
    assert len(result.created) > 0
    kinds = [r["kind"] for r in result.created]
    assert "run" in kinds
    assert "goal" in kinds
    assert "initiative" in kinds
    assert "plan" in kinds
    assert "slice" in kinds
    assert "decision" in kinds
    assert "risk" in kinds

    # Nothing was actually written
    assert list_records(workspace, "run") == []
    assert list_records(workspace, "goal") == []
    assert list_records(workspace, "slice") == []


def test_dry_run_with_existing_reused_records(workspace):
    bundle = load_bundle(FIXTURE)
    # Apply once to create records
    apply_bundle(workspace, bundle)
    # Dry run should show reuse
    result = apply_bundle(workspace, bundle, dry_run=True)
    assert len(result.reused) > 0


def test_dry_run_returns_no_events(workspace):
    bundle = load_bundle(FIXTURE)
    result = apply_bundle(workspace, bundle, dry_run=True)
    assert result.events == []
