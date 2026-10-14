# Codex Review Checklist

Verified against the current implementation, 57 passing tests, and offscreen Qt
checks. Existing checked clock/UI items are retained. Offscreen checks do not
verify desktop window-manager stacking or actual mouse interaction.

## Safety

- [ ] No code reads or writes `~/.config/pvfclock.conf`.
- [x] New config path is `~/.config/pvfclock2.yaml`.
- [x] Existing clock behavior is preserved.
- [x] Missing optional dependencies do not crash the app.
- [x] `sensors` execution has a timeout.

The main entry point uses only the new YAML configuration. The repository-wide
legacy-path item remains open: `config.py` still targets the old path, and the
three `digitalclock_modified*.py` scripts import it. The productive file was not
accessed during verification. Tests cover unavailable `psutil` and `sensors`.

## Architecture

- [x] Monitor panel is a separate window.
- [x] Parser code is separate from command execution.
- [x] Metrics collection is separate from UI rendering.
- [x] History buffer logic is bounded.
- [x] Sparklines do not add plotting dependencies.
- [x] Collection runs on a worker thread; widget updates run on the GUI thread.
- [x] Polling exceptions are logged and subsequent polls recover.
- [x] Reloads discard stale results; shutdown waits asynchronously for active collection.

## Config

- [x] Defaults are readable YAML.
- [x] Missing defaults merge into existing YAML.
- [x] User values are preserved.
- [ ] Labels, enablement, graph flags, interval, and history are configurable.
- [x] Invalid YAML reports the location and offers Exit or temporary defaults.
- [x] Temporary defaults cannot overwrite the file; successful reload restores saving.

The combined configurability item is only partially complete: temperature feature
graph flags override the group flag, disabling all metrics still shows placeholder
rows, and `monitor_panel.enabled` / `monitor_panel.scroll` are not consumed.
Labels, polling intervals, history duration/mode, and individual graph settings
are implemented. Full validation of configuration values remains outside the
completed YAML syntax/top-level mapping checks.

## UI

- [x] `Ctrl+1` toggles monitor panel.
- [x] Right click menu includes monitor toggle.
- [x] `Ctrl+Q` still quits.
- [x] Panel opens below clock.
- [x] Panel follows clock movement.
- [x] Scroll area works with additional sensors.
- [x] Calendar placement accounts for visible panel.

The menu action is registered with Qt's actions context-menu policy. An offscreen
check with 30 configured temperature rows verified vertical scrolling. Calendar
placement selects the visible panel or clock as its anchor, as confirmed in the
earlier offscreen smoke check. Real desktop stacking still needs manual validation.

## Tests and validation

- [x] Sensor parser tests exist.
- [x] Config tests exist.
- [x] History tests exist.
- [x] `python -m compileall .` passes.
- [x] `python -m pytest` passes or missing tooling is explained.

Commands run with the project virtualenv:

```bash
.venv/bin/python -m compileall -q .
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Result: compilation succeeded; **57 tests passed**.

## One-time alarm extension — implemented, desktop acceptance pending

The earlier 57-test result is the pre-alarm baseline. Current verification: 85
tests pass, including persistence/concurrency and offscreen alarm UI tests.
Desktop audio and window-manager acceptance remain manual.

- [x] One active alarm, with explicit set/replace/cancel and optional label/date.
- [x] Ctrl+2 and context-menu toggle; keyboard-first time entry and mouse controls.
- [x] Alarm setup/status panel always directly below clock, above visible monitor.
- [x] Docking and calendar placement follow all visibility, move, and resize changes.
- [x] Bell/time indicator and visible armed/fired/cancelled/missed status.
- [x] Alarm state/preferences stored only in the main `pvfclock2.yaml`.
- [x] Explicit defaults reset can clear alarm; normal merge/save preserves state.
- [x] Temporary defaults remain read-only and cannot arm an alarm.
- [x] All YAML writers use atomic coordinated mutations; stale saves cannot rearm.
- [x] Concurrent instances cannot claim the same alarm twice.
- [x] Future alarms survive restart; past startup alarms expire silently.
- [x] Running-session 10-second tolerance and sleep/clock-change rules are tested.
- [x] Fired state is persisted before sound/popup; write failures do not sound.
- [x] At most 30 seconds of sound, visible notification, dismissal, and cleanup.
- [x] Timezone/DST handling and malformed-record errors are covered.
- [x] No background scheduling, wakeup, recurrence, snooze, or additional alarms.
- [x] Automated alarm tests pass.
- [x] Manual desktop/audio and physical sleep/resume acceptance is recorded.
