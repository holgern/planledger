# planledger

A small CLI for storing structured, versioned implementation plans in a repository and rendering each plan into one self-contained Markdown handoff file.

## What it does

- stores independent plans under `.planledger/plans/plan-0001/`;
- versions every meaningful plan change;
- keeps each plan as modular component files;
- renders a standalone Markdown artifact for human or coding-agent handoff.

planledger is not a task manager, does not store goals, and does not depend on taskledger.

## Install

```bash
pip install -e .
```

## Quick start

```bash
planledger init
planledger plan create --title "Add feature A" --request "Please review how we can add feature A. Ask me questions when something is not clear."
planledger plan component set plan-0001 approach --file approach.md
planledger plan component set plan-0001 implementation_steps --file steps.md
planledger plan build plan-0001 --print
planledger plan status plan-0001 done --reason "Ready for coding agent handoff."
```

## Plan rules

1. Only plans exist.
2. Each plan is standalone.
3. Each editable section is a component file.
4. Meaningful plan changes increment the version.
5. The rendered Markdown file is the handoff artifact.

## Plan components

Each plan stores these components:

- `request`
- `summary`
- `context`
- `open_questions`
- `assumptions`
- `approach`
- `implementation_steps`
- `target_files`
- `validation`
- `risks`
- `rollback`
- `notes`

## Filesystem layout

```text
.planledger/
  storage.yaml
  plans/
    plan-0001/
      plan.yaml
      components/
      rendered/
      versions/
```

## CLI surface

```text
planledger init [--project-name NAME] [--planledger-dir .planledger] [--hidden-config]
planledger status [--json]
planledger doctor [--json]

planledger plan create --title TITLE [--request TEXT | --request-file PATH] [--status new|in_progress]
planledger plan list [--status STATUS] [--json]
planledger plan show PLAN_ID [--component KEY] [--rendered] [--json]
planledger plan status PLAN_ID STATUS --reason TEXT
planledger plan cancel PLAN_ID --reason TEXT
planledger plan component list PLAN_ID [--json]
planledger plan component show PLAN_ID COMPONENT
planledger plan component set PLAN_ID COMPONENT (--text TEXT | --file PATH) [--reason TEXT]
planledger plan component append PLAN_ID COMPONENT (--text TEXT | --file PATH) [--reason TEXT]
planledger plan build PLAN_ID [--out PATH] [--print] [--include-empty] [--json]
planledger plan validate PLAN_ID [--json]
planledger plan versions PLAN_ID [--json]
planledger plan diff PLAN_ID --from v0001 --to v0002
planledger plan apply --file plan.json [--dry-run]
```

## Structured bundle workflow

Agents can create or update plans through `planledger.structured_plan.v1` bundles:

```bash
planledger plan apply --file plan.json --dry-run
planledger plan apply --file plan.json
```

## Development

```bash
python -m pytest
python -m ruff check .
python -m mypy planledger
```
