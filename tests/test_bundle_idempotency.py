from __future__ import annotations

from pathlib import Path

import pytest

from planledger.bundle import apply_bundle, load_bundle
from planledger.storage import initialize_project, list_records

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "harness_bundle_v1.json"


@pytest.fixture
def workspace(tmp_path: Path):
    return initialize_project(tmp_path, "Bundle Idempotency")


def test_reapply_does_not_duplicate_records(workspace):
    bundle = load_bundle(FIXTURE)
    result1 = apply_bundle(workspace, bundle)
    result2 = apply_bundle(workspace, bundle)

    # Second apply should create a new run but reuse goal/initiative/slice
    assert len(result2.created) > 0  # At least run record
    assert len(result2.reused) > 0

    # Goal should still be one
    goals = list_records(workspace, "goal")
    assert len(goals) == 1

    # Initiative should still be one
    inits = list_records(workspace, "initiative")
    assert len(inits) == 1

    # Slice with same key should not be duplicated
    slices = list_records(workspace, "slice")
    assert len(slices) == 1


def test_reapply_creates_new_run(workspace):
    bundle = load_bundle(FIXTURE)
    apply_bundle(workspace, bundle)
    apply_bundle(workspace, bundle)

    runs = list_records(workspace, "run")
    assert len(runs) == 2
