# ruff: noqa: E501
from __future__ import annotations

from typing import Any

from planledger.models import Workspace
from planledger.storage import (
    active_initiative,
    latest_plan_for_initiative,
    lint_plan,
    list_records,
)
from planledger.taskledger import reconcile


def _action(
    action: str,
    next_command: str,
    *,
    next_item: dict[str, Any] | None = None,
    commands: list[dict[str, Any]] | None = None,
    blocking: list[Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": "planledger_next_action",
        "action": action,
        "next_command": next_command,
    }
    if next_item is not None:
        result["next_item"] = next_item
    if commands is not None:
        result["commands"] = commands
    if blocking is not None:
        result["blocking"] = blocking
    return result


def _cmd(
    kind: str,
    label: str,
    command: str,
    *,
    primary: bool = True,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "command": command,
        "primary": primary,
    }


def _action_for_missing_initiative(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is not None:
        return None
    initiatives = list_records(workspace, "initiative")
    if initiatives:
        target = initiatives[0]
        return _action(
            "activate-initiative",
            f"planledger initiative activate {target.record_id}",
            next_item={
                "kind": "initiative",
                "id": target.record_id,
                "title": target.front_matter.get("title"),
            },
            commands=[
                _cmd(
                    "complete",
                    "Activate initiative",
                    f"planledger initiative activate {target.record_id}",
                )
            ],
        )
    return _action(
        "create-initiative",
        'planledger initiative create "<title>" --goal goal-0001',
        commands=[
            _cmd(
                "complete",
                "Create initiative",
                'planledger initiative create "<title>" --goal goal-0001',
            )
        ],
    )


def _action_for_missing_plan(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is None:
        return None
    plan = latest_plan_for_initiative(workspace, active)
    if plan is not None:
        return None
    return _action(
        "plan-needed",
        f"planledger plan draft --initiative {active}",
        next_item={"kind": "initiative", "id": active},
        commands=[
            _cmd(
                "complete",
                "Draft plan",
                f"planledger plan draft --initiative {active}",
            )
        ],
    )


def _action_for_open_decision(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is None:
        return None
    decisions = [
        decision
        for decision in list_records(workspace, "decision")
        if decision.front_matter.get("initiative") == active
        and decision.front_matter.get("status") == "open"
    ]
    if not decisions:
        return None
    decision = decisions[0]
    return _action(
        "decision-needed",
        f"planledger option compare {decision.record_id}",
        next_item={
            "kind": "decision",
            "id": decision.record_id,
            "title": decision.front_matter.get("title"),
        },
        commands=[
            _cmd(
                "inspect",
                "Compare options",
                f"planledger option compare {decision.record_id}",
            ),
            _cmd(
                "complete",
                "Accept decision",
                (
                    f"planledger decision accept {decision.record_id} "
                    '--option OPT --rationale "..."'
                ),
                primary=False,
            ),
        ],
    )


def _action_for_draft_plan(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is None:
        return None
    plan = latest_plan_for_initiative(workspace, active)
    if plan is None or plan.front_matter.get("status") != "draft":
        return None
    lint = lint_plan(workspace, plan)
    if lint.issues:
        return _action(
            "fix-plan-lint",
            f"planledger plan lint {plan.record_id}",
            next_item={"kind": "plan", "id": plan.record_id},
            blocking=[{"kind": "lint", "reason": issue} for issue in lint.issues],
            commands=[
                _cmd(
                    "inspect",
                    "Run lint",
                    f"planledger plan lint {plan.record_id}",
                )
            ],
        )
    return _action(
        "accept-plan",
        f'planledger plan accept {plan.record_id} --note "Ready"',
        next_item={"kind": "plan", "id": plan.record_id},
        commands=[
            _cmd(
                "complete",
                "Accept plan",
                f'planledger plan accept {plan.record_id} --note "Ready"',
            )
        ],
    )


def _action_for_missing_milestones(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is None:
        return None
    plan = latest_plan_for_initiative(workspace, active)
    if plan is None:
        return None
    milestones = [
        milestone
        for milestone in list_records(workspace, "milestone")
        if milestone.front_matter.get("plan") == plan.record_id
    ]
    if milestones:
        return None
    return _action(
        "milestone-needed",
        f'planledger milestone add --plan {plan.record_id} "<title>"',
        next_item={"kind": "plan", "id": plan.record_id},
        commands=[
            _cmd(
                "complete",
                "Add milestone",
                f'planledger milestone add --plan {plan.record_id} "<title>"',
            )
        ],
    )


def _action_for_missing_slices(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is None:
        return None
    plan = latest_plan_for_initiative(workspace, active)
    if plan is None:
        return None
    milestones = [
        ms
        for ms in list_records(workspace, "milestone")
        if ms.front_matter.get("plan") == plan.record_id
    ]
    if not milestones:
        return None
    slices = [
        item
        for item in list_records(workspace, "slice")
        if item.front_matter.get("plan") == plan.record_id
    ]
    if slices:
        return None
    milestone = milestones[0]
    return _action(
        "slice-needed",
        f'planledger slice add --milestone {milestone.record_id} "<title>"',
        next_item={"kind": "milestone", "id": milestone.record_id},
        commands=[
            _cmd(
                "complete",
                "Add slice",
                f'planledger slice add --milestone {milestone.record_id} "<title>"',
            )
        ],
    )


def _action_for_shaping_slice(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is None:
        return None
    plan = latest_plan_for_initiative(workspace, active)
    if plan is None:
        return None
    slices = [
        item
        for item in list_records(workspace, "slice")
        if item.front_matter.get("plan") == plan.record_id
    ]
    shaping = [
        item
        for item in slices
        if item.front_matter.get("status") in {"idea", "shaping"}
    ]
    if not shaping:
        return None
    candidate = shaping[0]
    return _action(
        "slice-ready",
        f"planledger slice ready {candidate.record_id}",
        next_item={"kind": "slice", "id": candidate.record_id},
        commands=[
            _cmd(
                "complete",
                "Mark ready",
                f"planledger slice ready {candidate.record_id}",
            )
        ],
    )


def _action_for_ready_slice(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is None:
        return None
    plan = latest_plan_for_initiative(workspace, active)
    if plan is None:
        return None
    slices = [
        item
        for item in list_records(workspace, "slice")
        if item.front_matter.get("plan") == plan.record_id
    ]
    ready = [
        item
        for item in slices
        if item.front_matter.get("status") == "ready-for-execution"
    ]
    if not ready:
        return None
    candidate = ready[0]
    bindings = list(candidate.front_matter.get("taskledger_bindings") or [])
    if bindings:
        return None
    return _action(
        "push-taskledger",
        f"planledger taskledger push {candidate.record_id} --create-task",
        next_item={"kind": "slice", "id": candidate.record_id},
        commands=[
            _cmd(
                "complete",
                "Push to taskledger",
                (f"planledger taskledger push {candidate.record_id} --create-task"),
            )
        ],
    )


def _action_for_executing_slice(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is None:
        return None
    plan = latest_plan_for_initiative(workspace, active)
    if plan is None:
        return None
    slices = [
        item
        for item in list_records(workspace, "slice")
        if item.front_matter.get("plan") == plan.record_id
    ]
    executing = [
        item for item in slices if item.front_matter.get("status") == "in-execution"
    ]
    if not executing:
        return None
    candidate = executing[0]
    drift = reconcile(workspace).get("drift")
    if isinstance(drift, list) and drift:
        return _action(
            "reconcile-drift",
            "planledger taskledger reconcile",
            commands=[
                _cmd(
                    "inspect",
                    "Reconcile drift",
                    "planledger taskledger reconcile",
                )
            ],
            blocking=drift,
        )
    return _action(
        "pull-taskledger",
        f"planledger taskledger pull --slice {candidate.record_id}",
        next_item={"kind": "slice", "id": candidate.record_id},
        commands=[
            _cmd(
                "inspect",
                "Pull task status",
                (f"planledger taskledger pull --slice {candidate.record_id}"),
            )
        ],
    )


def _action_for_completed_slices(
    workspace: Workspace,
) -> dict[str, Any] | None:
    active = active_initiative(workspace)
    if active is None:
        return None
    plan = latest_plan_for_initiative(workspace, active)
    if plan is None:
        return None
    slices = [
        item
        for item in list_records(workspace, "slice")
        if item.front_matter.get("plan") == plan.record_id
    ]
    if not slices or not all(
        item.front_matter.get("status") in {"executed", "validated"} for item in slices
    ):
        return None
    return _action(
        "review-initiative",
        f"planledger initiative show {active}",
        next_item={"kind": "initiative", "id": active},
        commands=[
            _cmd(
                "inspect",
                "Review initiative",
                f"planledger initiative show {active}",
            )
        ],
    )


CHECKERS = [
    _action_for_missing_initiative,
    _action_for_missing_plan,
    _action_for_open_decision,
    _action_for_draft_plan,
    _action_for_missing_milestones,
    _action_for_missing_slices,
    _action_for_shaping_slice,
    _action_for_ready_slice,
    _action_for_executing_slice,
    _action_for_completed_slices,
]


def suggest_next_action(workspace: Workspace) -> dict[str, Any]:
    for checker in CHECKERS:
        action = checker(workspace)
        if action is not None:
            return action
    return _action(
        "inspect-status",
        "planledger status --full",
        commands=[_cmd("inspect", "Inspect status", "planledger status --full")],
    )
