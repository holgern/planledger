# ruff: noqa: B008
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer

from planledger import __version__
from planledger.bundle import apply_structured_plan_bundle, load_bundle
from planledger.errors import PlanledgerError
from planledger.models import AppContext, PlanStatus, Workspace
from planledger.render import build_plan
from planledger.storage import (
    DEFAULT_PLANLEDGER_DIR,
    PLANLEDGER_CONFIG_FILENAMES,
    append_component,
    compute_next_action,
    component_spec,
    create_plan,
    diff_versions,
    discover_workspace,
    doctor,
    initialize_project,
    latest_rendered_path,
    list_plans,
    list_versions,
    load_component_content,
    load_plan,
    load_workspace,
    plan_status_counts,
    plan_to_dict,
    read_input_text,
    set_component,
    set_plan_status,
    storage_data,
    validate_plan,
    version_label,
    workspace_root_from_context,
)

app = typer.Typer(help="Structured versioned planning files")
plan_app = typer.Typer(help="Plan commands")
component_app = typer.Typer(help="Plan component commands")
app.add_typer(plan_app, name="plan")
plan_app.add_typer(component_app, name="component")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    root: Path | None = typer.Option(None, "--root", help="Workspace root override"),
    cwd: Path | None = typer.Option(None, "--cwd", help="Current workspace"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON envelope"),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version",
    ),
) -> None:
    _ = version
    ctx.obj = AppContext(root=root, cwd=cwd, json_output=json_output)


def _context(ctx: typer.Context) -> AppContext:
    app_ctx = ctx.obj
    if not isinstance(app_ctx, AppContext):
        raise PlanledgerError("internal_error", "Missing application context.")
    return app_ctx


def _emit(
    app_ctx: AppContext,
    command: str,
    result: dict[str, Any],
    message: str,
) -> None:
    if app_ctx.json_output:
        typer.echo(
            json.dumps(
                {
                    "ok": True,
                    "command": command,
                    "result": result,
                    "events": [],
                },
                indent=2,
                default=str,
            )
        )
        return
    typer.echo(message)


def _emit_error(app_ctx: AppContext, command: str, error: PlanledgerError) -> None:
    if app_ctx.json_output:
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "command": command,
                    "error": error.to_dict(),
                },
                indent=2,
                default=str,
            )
        )
        return
    typer.echo(f"Error [{error.code}]: {error.message}")
    for item in error.remediation:
        typer.echo(f"- {item}")


def _run_command(
    ctx: typer.Context,
    command: str,
    fn: Callable[[], tuple[dict[str, Any], str]],
) -> None:
    app_ctx = _context(ctx)
    try:
        result, message = fn()
    except PlanledgerError as error:
        _emit_error(app_ctx, command, error)
        raise typer.Exit(code=error.exit_code) from error
    except Exception as error:  # pragma: no cover
        wrapped = PlanledgerError("internal_error", str(error))
        _emit_error(app_ctx, command, wrapped)
        raise typer.Exit(code=1) from error
    _emit(app_ctx, command, result, message)


def _require_workspace(ctx: typer.Context) -> Workspace:
    return load_workspace(_context(ctx))


def _summary_message(plan: dict[str, Any], verb: str) -> str:
    return (
        f"{verb} {plan['plan_id']} "
        f"({plan['status']}, {version_label(int(plan['version']))}) -> "
        f"{plan['latest_rendered_path']}"
    )


def _human_plan_details(plan: dict[str, Any]) -> str:
    lines = [
        plan["plan_id"],
        f"title: {plan['title']}",
        f"status: {plan['status']}",
        f"version: {version_label(int(plan['version']))}",
        f"path: {plan['path']}",
        f"rendered: {plan['latest_rendered_path']}",
    ]
    return "\n".join(lines)


@app.command()
def init(
    ctx: typer.Context,
    project_name: str | None = typer.Option(
        None,
        "--project-name",
        help="Project name",
    ),
    planledger_dir: str = typer.Option(
        DEFAULT_PLANLEDGER_DIR,
        "--planledger-dir",
        help="Planledger storage directory",
    ),
    hidden_config: bool = typer.Option(
        False,
        "--hidden-config",
        help="Write .planledger.toml instead of planledger.toml",
    ),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        app_ctx = _context(ctx)
        root = workspace_root_from_context(app_ctx)
        workspace = initialize_project(
            root=root,
            project_name=project_name or root.name,
            planledger_dir=planledger_dir,
            config_filename=".planledger.toml" if hidden_config else "planledger.toml",
        )
        result = {
            "root": str(workspace.root),
            "config_path": str(workspace.config_path),
            "planledger_dir": str(workspace.planledger_dir),
            "storage_path": str(workspace.storage_path),
            "supported_config_filenames": list(PLANLEDGER_CONFIG_FILENAMES),
        }
        return result, f"Initialized planledger in {workspace.root}"

    _run_command(ctx, "init", run)


@app.command()
def status(ctx: typer.Context) -> None:
    def run() -> tuple[dict[str, Any], str]:
        app_ctx = _context(ctx)
        workspace = discover_workspace(app_ctx)
        root = workspace_root_from_context(app_ctx)
        if workspace is None:
            return (
                {
                    "initialized": False,
                    "root": str(root),
                },
                "planledger is not initialized.",
            )
        data = storage_data(workspace)
        result = {
            "initialized": True,
            "root": str(workspace.root),
            "config_path": str(workspace.config_path),
            "planledger_dir": str(workspace.planledger_dir),
            "schema_version": data.get("schema_version"),
            "plan_count": len(list_plans(workspace)),
            "status_counts": plan_status_counts(workspace),
        }
        message = (
            f"Initialized workspace at {workspace.root} "
            f"with {result['plan_count']} plan(s)."
        )
        return result, message

    _run_command(ctx, "status", run)


@app.command("doctor")
def doctor_command(ctx: typer.Context) -> None:
    def run() -> tuple[dict[str, Any], str]:
        app_ctx = _context(ctx)
        workspace = discover_workspace(app_ctx)
        if workspace is None:
            result = {
                "healthy": False,
                "errors": ["planledger is not initialized."],
                "warnings": [],
            }
            return result, "healthy: false"
        result = doctor(workspace)
        summary = "healthy: true" if result["healthy"] else "healthy: false"
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        if isinstance(errors, list) and errors:
            summary += "\n" + "\n".join(f"- {item}" for item in errors)
        if isinstance(warnings, list) and warnings:
            summary += "\n" + "\n".join(f"- {item}" for item in warnings)
        return result, summary

    _run_command(ctx, "doctor", run)


@plan_app.command("create")
def plan_create(
    ctx: typer.Context,
    title: str = typer.Option(..., "--title", help="Plan title"),
    request: str | None = typer.Option(None, "--request", help="Inline request text"),
    request_file: Path | None = typer.Option(
        None,
        "--request-file",
        help="Request file",
    ),
    status: PlanStatus = typer.Option("new", "--status", help="Initial status"),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        request_text = read_input_text(request, request_file)
        created = create_plan(
            workspace,
            title=title,
            request=request_text,
            status=status,
        )
        built = build_plan(workspace, created.plan_id)
        return built, _summary_message(built, "Created")

    _run_command(ctx, "plan.create", run)


@plan_app.command("list")
def plan_list(
    ctx: typer.Context,
    status: PlanStatus | None = typer.Option(None, "--status", help="Filter by status"),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        plans = [plan_to_dict(plan) for plan in list_plans(workspace, status=status)]
        if not plans:
            return {"plans": []}, "No plans found."
        lines = [
            (
                f"{plan['plan_id']} {plan['title']} "
                f"[{plan['status']}] {version_label(int(plan['version']))}"
            )
            for plan in plans
        ]
        return {"plans": plans}, "\n".join(lines)

    _run_command(ctx, "plan.list", run)


@plan_app.command("show")
def plan_show(
    ctx: typer.Context,
    plan_id: str,
    component: str | None = typer.Option(None, "--component", help="Component key"),
    rendered: bool = typer.Option(
        False,
        "--rendered",
        help="Print latest rendered Markdown",
    ),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        plan = load_plan(workspace, plan_id)
        if component and rendered:
            raise PlanledgerError(
                "invalid_options",
                "Use either --component or --rendered, not both.",
            )
        result = plan_to_dict(plan)
        if component is not None:
            component_spec(component)
            content = load_component_content(plan, component)
            result["component"] = component
            result["content"] = content
            return result, content
        if rendered:
            latest = latest_rendered_path(plan)
            if not latest.exists():
                raise PlanledgerError(
                    "not_found",
                    f"No rendered artifact exists for {plan_id}.",
                )
            rendered_markdown = latest.read_text(encoding="utf-8")
            result["markdown"] = rendered_markdown
            return result, rendered_markdown
        return result, _human_plan_details(result)

    _run_command(ctx, "plan.show", run)


@plan_app.command("status")
def plan_status_command(
    ctx: typer.Context,
    plan_id: str,
    status: PlanStatus,
    reason: str = typer.Option(..., "--reason", help="Reason for the status change"),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        updated = set_plan_status(workspace, plan_id, status, reason)
        built = build_plan(workspace, updated.plan_id)
        return built, _summary_message(built, "Updated")

    _run_command(ctx, "plan.status", run)


@plan_app.command("cancel")
def plan_cancel(
    ctx: typer.Context,
    plan_id: str,
    reason: str = typer.Option(..., "--reason", help="Cancellation reason"),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        updated = set_plan_status(workspace, plan_id, "cancelled", reason)
        built = build_plan(workspace, updated.plan_id)
        return built, _summary_message(built, "Cancelled")

    _run_command(ctx, "plan.cancel", run)


@component_app.command("list")
def plan_component_list(ctx: typer.Context, plan_id: str) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        plan = load_plan(workspace, plan_id)
        result = {
            "plan_id": plan_id,
            "components": [
                {
                    "key": key,
                    "title": spec.title,
                    "path": spec.path,
                    "required": spec.required,
                    "order": spec.order,
                }
                for key, spec in sorted(
                    plan.components.items(),
                    key=lambda item: (item[1].order, item[0]),
                )
            ],
        }
        components = result["components"]
        assert isinstance(components, list)
        message = "\n".join(
            f"{item['key']} -> {item['path']}"
            for item in components
            if isinstance(item, dict)
        )
        return result, message

    _run_command(ctx, "plan.component.list", run)


@component_app.command("show")
def plan_component_show(ctx: typer.Context, plan_id: str, component: str) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        plan = load_plan(workspace, plan_id)
        component_spec(component)
        content = load_component_content(plan, component)
        return {
            "plan_id": plan_id,
            "component": component,
            "content": content,
        }, content

    _run_command(ctx, "plan.component.show", run)


@component_app.command("set")
def plan_component_set(
    ctx: typer.Context,
    plan_id: str,
    component: str,
    text: str | None = typer.Option(None, "--text", help="Inline component content"),
    file: Path | None = typer.Option(
        None,
        "--file",
        help="Read component content from file",
    ),
    reason: str | None = typer.Option(None, "--reason", help="Reason for the update"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Override cancelled plan protection",
    ),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        content = read_input_text(text, file)
        updated = set_component(
            workspace,
            plan_id,
            component,
            content,
            reason,
            force=force,
        )
        built = build_plan(workspace, updated.plan_id)
        return built, _summary_message(built, "Updated")

    _run_command(ctx, "plan.component.set", run)


@component_app.command("append")
def plan_component_append(
    ctx: typer.Context,
    plan_id: str,
    component: str,
    text: str | None = typer.Option(None, "--text", help="Inline component content"),
    file: Path | None = typer.Option(
        None,
        "--file",
        help="Read component content from file",
    ),
    reason: str | None = typer.Option(None, "--reason", help="Reason for the update"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Override cancelled plan protection",
    ),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        content = read_input_text(text, file)
        updated = append_component(
            workspace,
            plan_id,
            component,
            content,
            reason,
            force=force,
        )
        built = build_plan(workspace, updated.plan_id)
        return built, _summary_message(built, "Updated")

    _run_command(ctx, "plan.component.append", run)


@plan_app.command("build")
def plan_build(
    ctx: typer.Context,
    plan_id: str,
    out: Path | None = typer.Option(None, "--out", help="Write build output to path"),
    print_output: bool = typer.Option(False, "--print", help="Print rendered Markdown"),
    include_empty: bool = typer.Option(
        False,
        "--include-empty",
        help="Include empty optional sections",
    ),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        built = build_plan(workspace, plan_id, out=out, include_empty=include_empty)
        message = (
            built["markdown"] if print_output else _summary_message(built, "Built")
        )
        return built, message

    _run_command(ctx, "plan.build", run)


@plan_app.command("validate")
def plan_validate(ctx: typer.Context, plan_id: str) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        plan = load_plan(workspace, plan_id)
        errors = validate_plan(plan, for_done=plan.status == "done")
        result = {
            "plan_id": plan_id,
            "valid": not errors,
            "errors": errors,
        }
        if errors:
            return result, "\n".join(errors)
        return result, f"{plan_id} is valid."

    _run_command(ctx, "plan.validate", run)


@plan_app.command("versions")
def plan_versions(ctx: typer.Context, plan_id: str) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        plan = load_plan(workspace, plan_id)
        versions = list_versions(plan)
        return {
            "plan_id": plan_id,
            "versions": versions,
        }, "\n".join(versions) or "No versions."

    _run_command(ctx, "plan.versions", run)


@plan_app.command("diff")
def plan_diff(
    ctx: typer.Context,
    plan_id: str,
    from_version: str = typer.Option(..., "--from", help="From version label"),
    to_version: str = typer.Option(..., "--to", help="To version label"),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        diff = diff_versions(workspace, plan_id, from_version, to_version)
        return {
            "plan_id": plan_id,
            "from": from_version,
            "to": to_version,
            "diff": diff,
        }, diff

    _run_command(ctx, "plan.diff", run)


@plan_app.command("apply")
def plan_apply(
    ctx: typer.Context,
    file: Path = typer.Option(..., "--file", help="Structured plan bundle file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without writing"),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        workspace = _require_workspace(ctx)
        bundle = load_bundle(file)
        result = apply_structured_plan_bundle(workspace, bundle, dry_run=dry_run)
        if dry_run:
            return result, "Bundle dry-run passed."
        plan = result["plan"]
        assert isinstance(plan, dict)
        return result, _summary_message(plan, "Applied")

    _run_command(ctx, "plan.apply", run)
@app.command("next-action")
def next_action(
    ctx: typer.Context,
    plan_id: str | None = typer.Argument(None, help="Plan id"),
) -> None:
    def run() -> tuple[dict[str, Any], str]:
        app_ctx = _context(ctx)
        workspace = discover_workspace(app_ctx)
        result = compute_next_action(workspace, plan_id)
        lines = [f"next_item: {result['next_item']}"]
        if result.get('plan_id'):
            lines.append(f"plan_id: {result['plan_id']}")
        if result.get('status'):
            lines.append(f"status: {result['status']}")
        if result.get('next_command'):
            lines.append(f"next_command: {result['next_command']}")
        for blocker in result.get('blockers', []):
            lines.append(f"blocker: {blocker}")
        for error in result.get('validation_errors', []):
            lines.append(f"validation_error: {error}")
        return result, "\n".join(lines)

    _run_command(ctx, "next-action", run)
