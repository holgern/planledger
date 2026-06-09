---
name: planledger
description: Use planledger for independent structured plans and standalone Markdown handoff artifacts.
license: Apache-2.0
compatibility: opencode
metadata:
  audience: coding-agents
  workflow: planning
---

## skill_version: planledger-skill-v2

# Planledger Skill

Use planledger only for structured, versioned plans. The rendered Markdown artifact is the deliverable.

## Mandatory execution contract

When the user asks for planning work with planledger, the agent must use the planledger CLI.

Recommended first steps:

1. Run `planledger --json status`.
2. If the workspace is not initialized, run `planledger init`.
3. Create a new independent plan unless the user names an existing `plan-000X`.

## Core rules

1. For every new planning request, create a new independent plan unless the user names an existing plan id.
2. Ask clarifying questions in chat when required, but store known questions in the plan's `open_questions` component.
3. Do not create goals, milestones, slices, or taskledger tasks.
4. Keep each plan component focused:
   - `request` = original human request
   - `context` = repository facts
   - `open_questions` = unresolved issues
   - `assumptions` = assumed facts
   - `approach` = recommended architecture or design
   - `implementation_steps` = ordered coding steps
   - `target_files` = likely files
   - `validation` = commands and checks
   - `risks` = risks and mitigations
   - `rollback` = repair strategy
5. When the user asks for a change, update only the affected component, provide a reason, build the plan, and report the new version.
6. When the user approves, set status to `done` and build again.
7. The final answer to the user should reference the rendered Markdown path.

## Common workflow

```bash
planledger init
planledger plan create --title "Add feature A" --request-file /tmp/request.md
planledger plan component set plan-0001 context --file /tmp/context.md
planledger plan component set plan-0001 approach --file /tmp/approach.md
planledger plan component set plan-0001 implementation_steps --file /tmp/steps.md
planledger plan component set plan-0001 validation --file /tmp/validation.md
planledger plan build plan-0001
```

When revising a plan:

```bash
planledger plan status plan-0001 rework --reason "Human requested changes"
planledger plan component set plan-0001 implementation_steps --file /tmp/reworked-steps.md --reason "Split migration from UI change"
planledger plan build plan-0001
```

When the human signs off:

```bash
planledger plan status plan-0001 done --reason "Human accepted the plan"
planledger plan build plan-0001
```

## Bundle workflow

```bash
planledger plan apply --file plan.json --dry-run
planledger plan apply --file plan.json
```
