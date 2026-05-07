from __future__ import annotations

from pathlib import Path

import pytest

from planledger.backfill import backfill_apply, backfill_review
from planledger.storage import initialize_project, list_records

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "harness_bundle_v1.json"


@pytest.fixture
def workspace(tmp_path: Path):
    return initialize_project(tmp_path, "Backfill Test")


def test_backfill_apply_requires_evidence(workspace):
    with pytest.raises(Exception, match="missing_evidence"):
        backfill_apply(
            workspace,
            FIXTURE,
            provenance="inferred",
            evidence=None,
        )


def test_backfill_apply_with_evidence(workspace):
    result = backfill_apply(
        workspace,
        FIXTURE,
        evidence=[{"path": "README.md", "reason": "Inferred from docs"}],
    )
    assert result["provenance"] == "inferred"
    assert len(result["created"]) > 0


def test_backfill_apply_marks_records_inferred(workspace):
    backfill_apply(
        workspace,
        FIXTURE,
        evidence=[{"path": "README.md", "reason": "Inferred from docs"}],
    )
    goals = list_records(workspace, "goal")
    assert len(goals) == 1
    assert goals[0].front_matter.get("provenance") == "inferred"

    inits = list_records(workspace, "initiative")
    assert len(inits) == 1
    assert inits[0].front_matter.get("provenance") == "inferred"


def test_backfill_review_finds_inferred_records(workspace):
    backfill_apply(
        workspace,
        FIXTURE,
        evidence=[{"path": "README.md", "reason": "Inferred from docs"}],
    )
    result = backfill_review(workspace)
    assert result["inferred_count"] > 0
    kinds = [r["kind"] for r in result["records"]]
    assert "goal" in kinds
    assert "initiative" in kinds


def test_backfill_review_empty(workspace):
    result = backfill_review(workspace)
    assert result["inferred_count"] == 0
    assert result["records"] == []


def test_backfill_dry_run(workspace):
    result = backfill_apply(
        workspace,
        FIXTURE,
        evidence=[{"path": "README.md", "reason": "Inferred"}],
        dry_run=True,
    )
    assert result["dry_run"] is True
    goals = list_records(workspace, "goal")
    assert len(goals) == 0
