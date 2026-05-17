# Codex Prompts

## Repository inspection prompt

Read `CODEX_FEATURE_SPEC.md`, `CODEX_FEATURE_SPEC_EXTENDED.md`, and `AGENTS.md`. Inspect the repository and report:

- current file tree
- current entry point behavior
- references to old and new config paths
- duplicated or risky clock code
- proposed minimal implementation plan

Do not modify files yet.

## Config foundation prompt

Implement Phase 1 from `CODEX_IMPLEMENTATION_PLAN.md`. Add YAML config support for `~/.config/pvfclock2.yaml`, preserve current clock defaults, write defaults when missing, and deep merge new defaults into existing user YAML. Add tests for config path isolation and merge behavior. Do not read or write `~/.config/pvfclock.conf`.

Run:

```bash
python -m compileall .
python -m pytest
```

Report changed files and results.

## Sensor parser prompt

Implement Phase 2 from `CODEX_IMPLEMENTATION_PLAN.md`. Add a pure `sensors` output parser that extracts chip name, adapter, feature, numeric temperature value, and unit. Keep parser independent from subprocess execution. Add tests for CPU, GPU, NVMe, malformed lines, and ignored non-temperature values.

Run tests and report results.

## Panel shell prompt

Implement Phase 4 from `CODEX_IMPLEMENTATION_PLAN.md`. Add a separate frameless always-on-top monitor panel window, `Ctrl+1` action, context menu item, docking below the clock, and follow-on-move behavior. Use placeholder metric rows only. Keep existing clock behavior intact.

Run compile check and report manual GUI checks needed.

## Full feature completion prompt

Complete remaining phases from `CODEX_IMPLEMENTATION_PLAN.md`. Wire metrics provider, controller, history buffers, sparklines, temperature config mapping, and calendar placement. Keep changes minimal and tested.

Before final response, run:

```bash
python -m compileall .
python -m pytest
```

Report changed files, test results, manual checks, and known limitations.
