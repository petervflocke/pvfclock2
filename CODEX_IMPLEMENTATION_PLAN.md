# Codex Implementation Plan

Use this as the task sequence for the fold-down monitor feature.

## Phase 0, repository inspection

- Inspect current file tree.
- Identify current requirements file.
- Locate all references to `~/.config/pvfclock.conf`.
- Identify duplicated `showTime()` or style code.
- Do not edit productive config files.

## Phase 1, config foundation

Deliverables:

- `app_config.py`
- updated `requirements.txt`
- tests for config defaults and merge behavior

Acceptance:

- Missing config creates `~/.config/pvfclock2.yaml`.
- Existing user values survive default merges.
- Forbidden productive config path is not used.

## Phase 2, sensors parser

Deliverables:

- `sensors_parser.py`
- parser tests with sample `sensors` output

Acceptance:

- CPU `Tctl`, GPU `edge`, NVMe `Composite` style readings parse correctly.
- Non-temperature values are ignored for now.
- Unknown chips parse without code changes.

## Phase 3, metrics provider

Deliverables:

- `metrics_provider.py`
- tests for formatting and unavailable values

Acceptance:

- load uses `os.getloadavg()`.
- CPU uses `psutil.cpu_percent(interval=None)`.
- memory uses `psutil.virtual_memory()`.
- temperatures use `sensors` with timeout.
- missing dependencies or commands do not crash.

## Phase 4, panel shell

Deliverables:

- `monitor_panel.py`
- `Ctrl+1` action in main window
- context menu item

Acceptance:

- Panel is frameless and always on top.
- Panel opens below the clock.
- Panel follows clock movement and width.
- Panel uses scroll area.

## Phase 5, controller and history

Deliverables:

- `monitor_controller.py`
- bounded history buffers
- update timer based on YAML interval

Acceptance:

- History sample count follows `history_minutes * 60 / update_interval_seconds`.
- `always` and `panel_visible` modes work.
- UI shows current values and unavailable states.

## Phase 6, sparklines

Deliverables:

- `sparkline_widget.py`
- graph config integration

Acceptance:

- Graphs draw without extra plotting dependencies.
- Graphs can be enabled or disabled per metric group.

## Phase 7, calendar positioning

Deliverables:

- updated calendar placement logic

Acceptance:

- If panel is hidden, calendar opens under clock.
- If panel is visible, calendar opens under panel.

## Final validation command set

```bash
python -m compileall .
python -m pytest
python digitalclock.py
```

For GUI checks, run manually in the desktop session.

## Alarm extension implementation sequence

The original monitor phases remain historical. Implement this approved extension
incrementally, using the alarm section of the primary spec for final behavior.

1. Define the alarm record, state machine, timezone/date validation, startup versus
   running lateness rules, and pure tests with an injected clock.
2. Add `alarm` defaults to the main YAML and implement coordinated atomic mutations
   across every config writer. Preserve unrelated settings and terminal alarm
   states; test competing instances, stale geometry saves, failures, and reset.
3. Add a controller independent of monitor polling. Reconcile startup, arm/replace/
   cancel, claim before notification, silently expire missed alarms, and expose
   status. Keep configuration work and all waits off the GUI thread.
4. Add the Ctrl+2 editor/status panel, keyboard entry, date picker, mouse controls,
   explicit confirmation, and clock indicator. Disable arming in temporary mode.
5. Centralize docking: clock -> visible alarm -> visible monitor. Update on move,
   resize, height changes, and toggles; anchor/reposition the calendar below the
   lowest visible component. Preserve monitor fixed-width mode and Ctrl+1/Ctrl+Q.
6. Add the alarm popup and bounded sound with dismissal and shutdown cleanup.
   Choose/document the audio backend and bundled asset; test failure without
   replay. No blocking sound loop, snooze, recurrence, or background scheduling.
7. Run all automated checks and manual alarm acceptance scenarios from the test
   plan. Update review checkboxes only when verified; report desktop-only limits.

Alarm implementation status: phases 1–6 are implemented and covered by automated
checks. Phase 7 desktop audio/window-manager acceptance remains manual.
