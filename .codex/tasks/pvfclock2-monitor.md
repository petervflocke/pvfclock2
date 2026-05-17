# Task: Implement pvfclock2 fold-down monitor

## Read first

- `AGENTS.md`
- `CODEX_FEATURE_SPEC.md`
- `CODEX_FEATURE_SPEC_EXTENDED.md`
- `CODEX_IMPLEMENTATION_PLAN.md`
- `CODEX_TEST_PLAN.md`

## Goal

Implement the monitor panel feature from the product spec without affecting the productive app config.

## Hard constraints

- Never use `~/.config/pvfclock.conf`.
- Use `~/.config/pvfclock2.yaml`.
- Keep existing clock behavior.
- Use separate monitor panel window.
- Missing `psutil` or `sensors` must not crash.

## Done when

- Acceptance criteria in `CODEX_FEATURE_SPEC.md` pass.
- Review checklist passes.
- Compile and tests pass.
