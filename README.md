# planledger

Durable planning ledger for AI-assisted software work before taskledger execution.

## When to use it

Use planledger when you want machine-readable planning state (goal, initiative, plan, slices, decisions, risks), deterministic CLI workflows, and reliable handoff into taskledger.

## Install

```bash
pip install -e .
```

## Quick start

```bash
planledger init --project-name "My Project"
planledger goal create "Make release pipeline reliable"
planledger initiative create "Stabilize CI flow" --goal goal-0001
planledger initiative activate init-0001
planledger context export --json
```

## Harness workflow

1. Export current machine context:
   ```bash
   planledger context export --json --include-bodies --max-body-chars 4000
   ```
2. Agent reads project context + source code.
3. Agent emits `planledger.plan_bundle.v1` JSON.
4. Validate:
   ```bash
   planledger bundle validate --file bundle.json --json
   ```
5. Dry-run:
   ```bash
   planledger bundle apply --file bundle.json --dry-run --json
   ```
6. Apply:
   ```bash
   planledger bundle apply --file bundle.json --json
   ```

## Skill installation

```bash
mkdir -p ~/.agents/skills
cp -R ./skills/planledger ~/.agents/skills/planledger
```

## Bundle workflow

- Validate and apply planning bundles through `planledger bundle validate/apply`.
- Use `--dry-run` before apply in automation.
- Keep schema fixed to `planledger.plan_bundle.v1`.

## Taskledger integration

```bash
planledger taskledger detect --json
planledger taskledger push-plan plan-0001 --create-tasks --json
planledger taskledger pull --json
planledger taskledger reconcile --json
```

## Backfill workflow

Use backfill for existing projects:

```bash
planledger backfill apply --file baseline.json \
  --evidence README.md:Project\ purpose \
  --json
planledger backfill review --json
```

## Data model overview

Records are stored in `.planledger/ledgers/<ledger_ref>/` as Markdown/YAML records.
Core kinds:

- goal, initiative, plan, milestone, slice
- decision, option, risk
- binding, run, event

## JSON command envelope

All `--json` commands follow:

```json
{
  "ok": true,
  "command": "planledger.command",
  "result": {},
  "events": []
}
```

## Development

```bash
python -m pytest -q
```
