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

## One-time alarm implementation prompt (implemented design reference)

Implement the alarm extension sequence in `CODEX_IMPLEMENTATION_PLAN.md`, following
`CODEX_FEATURE_SPEC.md` and its engineering extension. One active alarm only;
missed alarms expire silently. Ctrl+2 toggles an editor/status panel directly below
the clock and ABOVE any visible monitor; update monitor/calendar positions on all
stack changes. Provide keyboard-first time entry, optional mouse controls/date
picker, label, explicit set/replace/cancel, and a clock indicator.

Store all alarm preferences/state in `~/.config/pvfclock2.yaml`. Defaults may clear
to an empty alarm on explicit reset. Normal merges/saves must preserve persisted
state. Temporary defaults remain read-only; no separate alarm config file. Apply
atomic coordinated read/modify/write to all YAML writers, so concurrent instances
and stale snapshots cannot duplicate or resurrect an alarm. Persist a fired claim
before notifying; failures must not sound an unrecorded alarm. Startup past alarms
are missed; running-session lateness tolerance is 10 seconds.

Add independent nonblocking alarm checks, notification, at most 30 seconds of
sound, and dismissal. No background scheduling, wake timer, snooze, recurrence, or
multiple alarms. Add the tests/manual checks specified in `CODEX_TEST_PLAN.md`.
Preserve existing monitoring, configuration recovery, and quit behavior. Never
access the productive legacy config. Run compileall and headless pytest; report
results and remaining manual audio/desktop checks. Do not mark planned checklist
items complete without evidence.
