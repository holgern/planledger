from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from planledger.context import export_context
from planledger.storage import initialize_project


def test_context_export_does_not_call_taskledger_by_default(
    tmp_path: Path,
) -> None:
    workspace = initialize_project(tmp_path, "Purity Test")
    with patch("planledger.taskledger.subprocess.run") as mock_run:
        export_context(workspace)
        mock_run.assert_not_called()


def test_context_export_with_allow_external_includes_next_action(
    tmp_path: Path,
) -> None:
    workspace = initialize_project(tmp_path, "External Test")
    result = export_context(workspace, allow_external=True)
    assert "next_action" in result
    assert result["next_action"]["action"] == "create-initiative"


def test_context_export_without_allow_external_has_safe_next_action(
    tmp_path: Path,
) -> None:
    workspace = initialize_project(tmp_path, "Safe Test")
    result = export_context(workspace, allow_external=False)
    assert "next_action" in result
    assert result["next_action"]["action"] == "inspect-status"
