from __future__ import annotations

from planledger.bundle import validate_bundle


def test_valid_bundle_passes():
    bundle = {
        "schema": "planledger.plan_bundle.v1",
        "request": {"title": "Test"},
        "plan": {"title": "Test plan", "objectives": ["Do thing"]},
        "milestones": [{"title": "M1", "slices": [{"title": "S1"}]}],
        "decisions": [{"title": "D1", "status": "open"}],
        "risks": [{"title": "R1", "impact": "high"}],
    }
    errors = validate_bundle(bundle)
    assert errors == []


def test_missing_schema():
    bundle = {"plan": {"title": "T", "objectives": ["O"]}}
    errors = validate_bundle(bundle)
    assert any("schema" in e for e in errors)


def test_wrong_schema():
    bundle = {
        "schema": "wrong",
        "request": {"title": "T"},
        "plan": {"title": "T", "objectives": ["O"]},
    }
    errors = validate_bundle(bundle)
    assert any("schema" in e for e in errors)


def test_missing_plan():
    bundle = {
        "schema": "planledger.plan_bundle.v1",
        "request": {"title": "T"},
    }
    errors = validate_bundle(bundle)
    assert any("plan" in e for e in errors)


def test_missing_plan_title():
    bundle = {
        "schema": "planledger.plan_bundle.v1",
        "request": {"title": "T"},
        "plan": {"objectives": ["O"]},
    }
    errors = validate_bundle(bundle)
    assert any("title" in e.lower() for e in errors)


def test_missing_plan_objectives():
    bundle = {
        "schema": "planledger.plan_bundle.v1",
        "request": {"title": "T"},
        "plan": {"title": "T"},
    }
    errors = validate_bundle(bundle)
    assert any("objectives" in e.lower() for e in errors)


def test_missing_request():
    bundle = {
        "schema": "planledger.plan_bundle.v1",
        "plan": {"title": "T", "objectives": ["O"]},
    }
    errors = validate_bundle(bundle)
    assert any("request" in e for e in errors)


def test_milestone_missing_title():
    bundle = {
        "schema": "planledger.plan_bundle.v1",
        "request": {"title": "T"},
        "plan": {"title": "T", "objectives": ["O"]},
        "milestones": [{"slices": []}],
    }
    errors = validate_bundle(bundle)
    assert any("title" in e.lower() for e in errors)


def test_milestone_slice_missing_title():
    bundle = {
        "schema": "planledger.plan_bundle.v1",
        "request": {"title": "T"},
        "plan": {"title": "T", "objectives": ["O"]},
        "milestones": [{"title": "M", "slices": [{}]}],
    }
    errors = validate_bundle(bundle)
    assert any("slice" in e.lower() and "title" in e.lower() for e in errors)


def test_decisions_not_list():
    bundle = {
        "schema": "planledger.plan_bundle.v1",
        "request": {"title": "T"},
        "plan": {"title": "T", "objectives": ["O"]},
        "decisions": "not a list",
    }
    errors = validate_bundle(bundle)
    assert any("decisions" in e for e in errors)


def test_risks_not_list():
    bundle = {
        "schema": "planledger.plan_bundle.v1",
        "request": {"title": "T"},
        "plan": {"title": "T", "objectives": ["O"]},
        "risks": "not a list",
    }
    errors = validate_bundle(bundle)
    assert any("risks" in e for e in errors)
