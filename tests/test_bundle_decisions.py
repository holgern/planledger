from __future__ import annotations

from pathlib import Path

import pytest

from planledger.bundle import apply_bundle, load_bundle
from planledger.storage import initialize_project, list_records

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "harness_bundle_v1.json"


@pytest.fixture
def workspace(tmp_path: Path):
    return initialize_project(tmp_path, "Decision Test")


def test_accepted_decision_sets_chosen_option(workspace):
    bundle = load_bundle(FIXTURE)
    apply_bundle(workspace, bundle)

    decisions = list_records(workspace, "decision")
    assert len(decisions) == 1
    dec = decisions[0]
    assert dec.front_matter.get("status") == "accepted"

    options = list_records(workspace, "option")
    accepted_options = [
        o for o in options if o.front_matter.get("status") == "accepted"
    ]
    assert len(accepted_options) == 1

    chosen = dec.front_matter.get("chosen_option")
    assert chosen is not None
    assert chosen == accepted_options[0].record_id


def test_accepted_decision_sets_accepted_at(workspace):
    bundle = load_bundle(FIXTURE)
    apply_bundle(workspace, bundle)

    decisions = list_records(workspace, "decision")
    assert len(decisions) == 1
    dec = decisions[0]
    assert dec.front_matter.get("status") == "accepted"
    assert dec.front_matter.get("accepted_at") is not None
