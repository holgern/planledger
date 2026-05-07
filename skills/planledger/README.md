# Planledger Agent Skill

This directory contains the planledger agent skill. Install it into your agent harness skills directory.

## Installation

```bash
mkdir -p ~/.agents/skills
cp -R ./skills/planledger ~/.agents/skills/planledger
```

## Usage

After installation, ask the harness or agent to load the `planledger` skill before planning or taskledger handoff work.

The skill teaches the agent how to use planledger as a hidden durable planning control plane: export context, validate and apply plan bundles, push work to taskledger, manage architectural decisions, and backfill existing projects.

## What this skill provides

- Default harness workflow for planning features
- Planning mode guidance (skip, light, full, repair)
- Required bundle properties for `planledger.plan_bundle.v1`
- Human interaction rules to avoid unnecessary questions
- Command reference for context export, bundle apply, taskledger push-plan, ADR, and backfill
