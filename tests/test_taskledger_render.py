from __future__ import annotations

from pathlib import Path

from planledger.models import Record
from planledger.taskledger_render import render_taskledger_description


def _make_record(
    kind: str,
    record_id: str,
    front_matter: dict,
    body: str = "",
) -> Record:
    return Record(
        kind=kind,
        record_id=record_id,
        path=Path(f"/tmp/{record_id}.md"),
        front_matter=front_matter,
        body=body,
    )


def test_minimal_render():
    sl = _make_record("slice", "slice-0001", {"title": "My slice"})
    plan = _make_record("plan", "plan-0001", {"title": "My plan"})
    ms = _make_record("milestone", "ms-0001", {"title": "MS1"})

    result = render_taskledger_description(
        slice_record=sl,
        plan=plan,
        milestone=ms,
        decisions=[],
        risks=[],
    )
    assert "# My slice" in result
    assert "plan-0001" in result
    assert "ms-0001" in result
    assert "slice-0001" in result


def test_render_with_objective():
    sl = _make_record(
        "slice",
        "slice-0001",
        {"title": "S1", "objective": "Do the thing."},
    )
    plan = _make_record("plan", "plan-0001", {"title": "P1"})
    ms = _make_record("milestone", "ms-0001", {"title": "M1"})

    result = render_taskledger_description(
        slice_record=sl,
        plan=plan,
        milestone=ms,
        decisions=[],
        risks=[],
    )
    assert "## Objective" in result
    assert "Do the thing." in result


def test_render_with_target_files():
    sl = _make_record(
        "slice",
        "slice-0001",
        {"title": "S1", "target_files": ["foo.py", "bar.py"]},
    )
    plan = _make_record("plan", "plan-0001", {"title": "P1"})
    ms = _make_record("milestone", "ms-0001", {"title": "M1"})

    result = render_taskledger_description(
        slice_record=sl,
        plan=plan,
        milestone=ms,
        decisions=[],
        risks=[],
    )
    assert "## Target files" in result
    assert "`foo.py`" in result


def test_render_with_implementation_steps():
    sl = _make_record(
        "slice",
        "slice-0001",
        {"title": "S1", "implementation_steps": ["Step A", "Step B"]},
    )
    plan = _make_record("plan", "plan-0001", {"title": "P1"})
    ms = _make_record("milestone", "ms-0001", {"title": "M1"})

    result = render_taskledger_description(
        slice_record=sl,
        plan=plan,
        milestone=ms,
        decisions=[],
        risks=[],
    )
    assert "## Implementation steps" in result
    assert "1. Step A" in result
    assert "2. Step B" in result


def test_render_with_acceptance_criteria():
    sl = _make_record(
        "slice",
        "slice-0001",
        {"title": "S1", "acceptance_criteria": ["Works", "Fast"]},
    )
    plan = _make_record("plan", "plan-0001", {"title": "P1"})
    ms = _make_record("milestone", "ms-0001", {"title": "M1"})

    result = render_taskledger_description(
        slice_record=sl,
        plan=plan,
        milestone=ms,
        decisions=[],
        risks=[],
    )
    assert "## Acceptance criteria" in result
    assert "- [ ] Works" in result


def test_render_with_validation_commands():
    sl = _make_record(
        "slice",
        "slice-0001",
        {"title": "S1", "validation_commands": ["pytest -q"]},
    )
    plan = _make_record("plan", "plan-0001", {"title": "P1"})
    ms = _make_record("milestone", "ms-0001", {"title": "M1"})

    result = render_taskledger_description(
        slice_record=sl,
        plan=plan,
        milestone=ms,
        decisions=[],
        risks=[],
    )
    assert "## Validation commands" in result
    assert "pytest -q" in result


def test_render_with_decisions():
    sl = _make_record("slice", "slice-0001", {"title": "S1"})
    plan = _make_record("plan", "plan-0001", {"title": "P1"})
    ms = _make_record("milestone", "ms-0001", {"title": "M1"})
    dec = _make_record(
        "decision",
        "dec-0001",
        {
            "title": "Use bundles",
            "status": "accepted",
            "chosen_option": "opt-0001",
            "decision_type": "architecture",
        },
    )

    result = render_taskledger_description(
        slice_record=sl,
        plan=plan,
        milestone=ms,
        decisions=[dec],
        risks=[],
    )
    assert "## Related decisions" in result
    assert "dec-0001" in result
    assert "architecture" in result


def test_render_with_risks():
    sl = _make_record("slice", "slice-0001", {"title": "S1"})
    plan = _make_record("plan", "plan-0001", {"title": "P1"})
    ms = _make_record("milestone", "ms-0001", {"title": "M1"})
    risk = _make_record(
        "risk",
        "risk-0001",
        {
            "title": "Data loss",
            "impact": "high",
            "mitigation": "Backup first.",
        },
    )

    result = render_taskledger_description(
        slice_record=sl,
        plan=plan,
        milestone=ms,
        decisions=[],
        risks=[risk],
    )
    assert "## Risks" in result
    assert "Data loss" in result
    assert "high" in result
    assert "Backup first." in result
