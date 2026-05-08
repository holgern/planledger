from __future__ import annotations

from pathlib import Path

import pytest

from planledger.backfill import backfill_apply
from planledger.storage import initialize_project, list_records

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "harness_bundle_v1.json"


@pytest.fixture
def workspace(tmp_path: Path):
    return initialize_project(tmp_path, "Backfill Evidence Test")


def test_backfill_stores_evidence_on_run(workspace):
    evidence = [{"path": "README.md", "reason": "Project purpose"}]
    backfill_apply(workspace, FIXTURE, evidence=evidence)

    runs = list_records(workspace, "run")
    assert len(runs) == 1
    run = runs[0]
    source_context = run.front_matter.get("source_context")
    assert source_context is not None
    assert source_context == evidence


def test_backfill_stores_multiple_evidence_items(workspace):
    evidence = [
        {"path": "README.md", "reason": "Project purpose"},
        {"path": "tests/test_core.py", "reason": "Existing behavior"},
    ]
    backfill_apply(workspace, FIXTURE, evidence=evidence)

    runs = list_records(workspace, "run")
    assert len(runs) == 1
    assert len(runs[0].front_matter.get("source_context", [])) == 2


def test_backfill_without_evidence_stores_empty(workspace):
    backfill_apply(workspace, FIXTURE, provenance="agent-generated")

    runs = list_records(workspace, "run")
    assert len(runs) == 1
    assert runs[0].front_matter.get("source_context") == []
