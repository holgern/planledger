from __future__ import annotations

from pathlib import Path

from planledger.storage import compute_next_action, initialize_project


def test_next_action_uninitialized() -> None:
    result = compute_next_action(None)
    assert result["workspace_initialized"] is False
    assert result["next_item"] == "init"
    assert result["plan_id"] is None


def test_next_action_no_plans(tmp_path: Path) -> None:
    workspace = initialize_project(
        root=tmp_path, project_name="test", planledger_dir=".planledger"
    )
    result = compute_next_action(workspace)
    assert result["workspace_initialized"] is True
    assert result["next_item"] == "create_plan"
    assert result["plan_id"] is None


def test_next_action_empty_required_components(
    initialized_workspace: Path, invoke
) -> None:
    create = invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Test",
        "--request",
        "Test request.",
    )
    assert create.exit_code == 0, create.stdout

    result, payload = (
        invoke(initialized_workspace, "--json", "next-action"),
        None,
    )
    import json

    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["next_item"] == "fill_component"
    assert payload["result"]["plan_id"] == "plan-0001"


def test_next_action_with_explicit_plan_id(initialized_workspace: Path, invoke) -> None:
    create = invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Test",
        "--request",
        "Test request.",
    )
    assert create.exit_code == 0, create.stdout

    import json

    result = invoke(initialized_workspace, "--json", "next-action", "plan-0001")
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["plan_id"] == "plan-0001"


def test_next_action_done_plan(initialized_workspace: Path, invoke) -> None:
    from tests.test_plan_status import _fill_required_components

    create = invoke(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Test",
        "--request",
        "Test request.",
    )
    assert create.exit_code == 0, create.stdout
    _fill_required_components(initialized_workspace, invoke)

    done = invoke(
        initialized_workspace,
        "plan",
        "status",
        "plan-0001",
        "done",
        "--reason",
        "Ready.",
    )
    assert done.exit_code == 0, done.stdout

    import json

    result = invoke(initialized_workspace, "--json", "next-action")
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["next_item"] == "handoff_ready"
    assert payload["result"]["plan_id"] == "plan-0001"


def test_next_action_prefers_active_plan(initialized_workspace: Path, invoke) -> None:
    for i in range(2):
        create = invoke(
            initialized_workspace,
            "plan",
            "create",
            "--title",
            f"Plan {i}",
            "--request",
            f"Request {i}.",
        )
        assert create.exit_code == 0, create.stdout

    import json

    result = invoke(initialized_workspace, "--json", "next-action")
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["plan_id"] == "plan-0002"


def test_next_action_explicit_plan_overrides_active(
    initialized_workspace: Path, invoke
) -> None:
    for i in range(2):
        create = invoke(
            initialized_workspace,
            "plan",
            "create",
            "--title",
            f"Plan {i}",
            "--request",
            f"Request {i}.",
        )
        assert create.exit_code == 0, create.stdout

    import json

    result = invoke(initialized_workspace, "--json", "next-action", "plan-0001")
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["plan_id"] == "plan-0001"


def test_next_action_is_read_only(initialized_workspace: Path, invoke) -> None:
    import json

    # Run twice, confirm no side effects
    result1 = invoke(initialized_workspace, "--json", "next-action")
    result2 = invoke(initialized_workspace, "--json", "next-action")
    p1 = json.loads(result1.stdout)
    p2 = json.loads(result2.stdout)
    assert p1["result"] == p2["result"]
