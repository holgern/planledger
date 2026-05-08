from __future__ import annotations

from typing import Any

from planledger.models import Workspace
from planledger.next_action import suggest_next_action
from planledger.storage import (
    active_initiative,
    latest_plan_for_initiative,
    list_events,
    list_records,
    load_record,
    record_counts,
)


def _record_summary(
    record: Any,
    include_body: bool = False,
    max_body_chars: int = 4000,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "id": record.record_id,
        "kind": record.kind,
        "front_matter": dict(record.front_matter),
    }
    if include_body:
        body = record.body
        if len(body) > max_body_chars:
            body = body[:max_body_chars] + "\n... (truncated)"
        summary["body"] = body
    return summary


def export_context(
    workspace: Workspace,
    *,
    include_taskledger: bool = False,
    include_bodies: bool = False,
    max_body_chars: int = 4000,
    max_events: int = 0,
    allow_external: bool = False,
) -> dict[str, Any]:
    project_config = workspace.config.get("project", {})

    result: dict[str, Any] = {
        "kind": "planledger_context_export",
        "schema": "planledger.context.v1",
        "project": {
            "name": project_config.get("name", "Planledger"),
            "root": str(workspace.root),
            "ledger_ref": workspace.ledger_ref,
        },
    }

    active: dict[str, Any] = {}
    active_init_id = active_initiative(workspace)
    if active_init_id is not None:
        try:
            initiative = load_record(
                workspace,
                "initiative",
                active_init_id,
            )
            active["initiative"] = _record_summary(
                initiative,
                include_body=include_bodies,
                max_body_chars=max_body_chars,
            )

            goal_ref = initiative.front_matter.get("goal")
            if goal_ref is not None:
                try:
                    goal = load_record(workspace, "goal", str(goal_ref))
                    active["goal"] = _record_summary(
                        goal,
                        include_body=include_bodies,
                        max_body_chars=max_body_chars,
                    )
                except Exception:
                    active["goal"] = {
                        "id": str(goal_ref),
                        "kind": "goal",
                        "error": "not_found",
                    }

            latest_plan = latest_plan_for_initiative(
                workspace,
                active_init_id,
            )
            if latest_plan is not None:
                active["latest_plan"] = _record_summary(
                    latest_plan,
                    include_body=include_bodies,
                    max_body_chars=max_body_chars,
                )
        except Exception:
            active["initiative"] = {
                "id": active_init_id,
                "error": "not_found",
            }

    result["active"] = active

    all_decisions = list_records(workspace, "decision")
    open_decisions = [
        _record_summary(
            d,
            include_body=include_bodies,
            max_body_chars=max_body_chars,
        )
        for d in all_decisions
        if d.front_matter.get("status") == "open"
    ]

    all_risks = list_records(workspace, "risk")
    risks = [
        _record_summary(
            r,
            include_body=include_bodies,
            max_body_chars=max_body_chars,
        )
        for r in all_risks
        if r.front_matter.get("status") == "open"
    ]

    all_slices = list_records(workspace, "slice")
    ready_slices = [
        _record_summary(
            s,
            include_body=include_bodies,
            max_body_chars=max_body_chars,
        )
        for s in all_slices
        if s.front_matter.get("status") == "ready-for-execution"
    ]
    executing_slices = [
        _record_summary(
            s,
            include_body=include_bodies,
            max_body_chars=max_body_chars,
        )
        for s in all_slices
        if s.front_matter.get("status") == "in-execution"
    ]

    all_bindings = list_records(workspace, "binding")
    bindings = [
        _record_summary(
            b,
            include_body=include_bodies,
            max_body_chars=max_body_chars,
        )
        for b in all_bindings
    ]

    result["records"] = {
        "open_decisions": open_decisions,
        "risks": risks,
        "ready_slices": ready_slices,
        "executing_slices": executing_slices,
        "bindings": bindings,
    }

    if include_taskledger:
        try:
            from planledger.taskledger import detect

            result["taskledger"] = detect(workspace)
        except Exception:
            result["taskledger"] = {"detected": False}

    if max_events > 0:
        events = list_events(workspace, limit=max_events)
        if events:
            result["recent_events"] = events
    result["counts"] = record_counts(workspace)
    if allow_external:
        result["next_action"] = suggest_next_action(workspace)
    else:
        result["next_action"] = {
            "kind": "planledger_next_action",
            "action": "inspect-status",
            "next_command": "planledger status --full",
            "note": "allow_external=False; full next action skipped",
        }

    return result
