from __future__ import annotations

from pathlib import Path


def test_json_success_envelope(initialized_workspace: Path, invoke_json) -> None:
    result, payload = invoke_json(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Add feature A",
        "--request",
        "Please review how we can add feature A.",
    )

    assert result.exit_code == 0, result.stdout
    assert payload["ok"] is True
    assert payload["command"] == "plan.create"
    assert "result" in payload
    assert payload["events"] == []


def test_json_error_envelope(initialized_workspace: Path, invoke_json) -> None:
    create_result, _ = invoke_json(
        initialized_workspace,
        "plan",
        "create",
        "--title",
        "Add feature A",
        "--request",
        "Please review how we can add feature A.",
    )
    result, payload = invoke_json(
        initialized_workspace,
        "plan",
        "component",
        "set",
        "plan-0001",
        "unknown_component",
        "--text",
        "text",
    )

    assert create_result.exit_code == 0, create_result.stdout
    assert result.exit_code != 0
    assert payload["ok"] is False
    assert payload["command"] == "plan.component.set"
    assert set(payload["error"]) >= {"code", "message", "remediation"}
