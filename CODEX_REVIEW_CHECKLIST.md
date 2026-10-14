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
