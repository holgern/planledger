---
name: planledger
description: Use planledger as a hidden durable planning control plane. The human does not need to read plan Markdown.
license: Apache-2.0
compatibility: opencode
metadata:
  audience: coding-agents
  workflow: task-management
---

## skill_version: planledger-skill-v1

# Planledger Skill

Use planledger as a hidden durable planning control plane. The human does not need to read plan Markdown.

## Mandatory execution contract

When this skill is loaded for planning, architecture, cross-module changes, ADR work, migration work, or taskledger handoff, the agent MUST use the planledger CLI. Reading this skill is not sufficient.

First action after loading this skill:

1. Run `planledger --json status`.
2. If the workspace is not initialized and the user asked for planning in the current project, run `planledger init --project-name "<project>"`, then run `planledger --json status` again.
3. Run `planledger --json context export --include-bodies --max-body-chars 4000` before drafting a bundle.

The agent MUST NOT skip planledger when the user explicitly asks to use planledger, asks for a planledger bundle, asks for taskledger handoff, or the request involves architecture, cross-module workflow, migrations, ADRs, backfill, or repair.

## Default workflow

1. `planledger --json status`
2. `planledger --json context export --include-bodies --max-body-chars 4000`
3. Read relevant source and prior planledger state.
4. Write a `planledger.plan_bundle.v1` JSON file.
5. `planledger --json bundle validate --file bundle.json`
6. `planledger --json bundle apply --file bundle.json --dry-run`
7. `planledger --json bundle apply --file bundle.json`
8. Read `result.plan_id` from the apply output. Never hardcode `plan-0001` unless it is actually the returned id.
9. If executable slices are ready or the user requested taskledger implementation handoff:
   - `planledger --json taskledger detect`
   - `planledger --json taskledger push-plan <result.plan_id> --create-tasks`
   - If the result has zero created tasks, report that handoff did not complete and why. Do not claim taskledger handoff succeeded.
10. Final response must include the plan id, whether bundle validation passed, whether dry-run passed, whether apply passed, and whether taskledger tasks were created or skipped.

## Human interaction rules

- Do not ask the human to inspect plan Markdown in the happy path.
- Ask questions only when the request is blocked by missing requirements.
- Prefer recording assumptions as planledger records over asking low-value questions.
- Keep plans compact enough to be useful as future AI memory.

## When to skip planning

Skip planledger for trivial one-file edits with obvious implementation and low risk unless the user explicitly asks for planning.

Use full planledger workflow for architecture, migrations, new workflows, cross-module changes, taskledger handoff, or any request involving ADRs/decisions.

## Planning modes

| Mode   | When to use                                                                     |
| ------ | ------------------------------------------------------------------------------- |
| skip   | Trivial one-file edit, obvious bug, no architecture impact.                     |
| light  | Small feature, 1-3 files, low ambiguity.                                        |
| full   | Cross-module change, schema/API/workflow change, migration, taskledger handoff. |
| repair | Failed previous run, drift, validation failure, unclear state.                  |

## Required bundle properties

Every executable slice in a `planledger.plan_bundle.v1` bundle should include:

- objective
- target files
- implementation steps
- acceptance criteria
- validation commands
- risks or assumptions if relevant
- taskledger readiness flag

## Context export

Use `planledger --json context export` to get a snapshot of current planning state including active goal, initiative, plan, open decisions, risks, ready slices, bindings, and next action.

## Bundle commands

```bash
planledger --json bundle validate --file bundle.json
planledger --json bundle apply --file bundle.json --dry-run
planledger --json bundle apply --file bundle.json
```

## Taskledger handoff

```bash
planledger --json taskledger detect
planledger --json taskledger push-plan <plan-id-from-apply-result> --create-tasks
planledger --json taskledger push-plan <plan-id-from-apply-result> --dry-run
```

## ADR commands

```bash
planledger adr create "Decision title" --initiative init-0001
planledger --json adr list --initiative init-0001
planledger adr accept dec-0001 --option opt-0001 --rationale "..."
```

## Backfill for existing projects

```bash
planledger --json backfill apply --file baseline.json
planledger --json backfill review
```

## Final response evidence checklist

Before answering the human, verify and report:

- status/context export was run
- bundle validate passed
- bundle apply dry-run passed
- bundle apply passed
- returned plan id was captured
- taskledger detect was run when handoff was requested
- taskledger push-plan was run with `--create-tasks` when handoff was requested
- taskledger push-plan created tasks, or the response explicitly says why none were created
