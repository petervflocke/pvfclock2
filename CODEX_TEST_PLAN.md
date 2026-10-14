# Codex Test Plan

## Automated tests

Create tests under `tests/` for pure Python logic.

### Config tests

- `test_default_config_path_is_pvfclock2_yaml`
- `test_default_config_is_written_when_missing`
- `test_existing_user_values_are_preserved_on_merge`
- `test_legacy_config_path_is_never_used`

Configuration recovery tests in `tests/test_config_recovery.py` cover parser line/column
and source text, invalid top-level documents, both startup dialog choices, blocked
saving with temporary defaults, and recovery through Reload Config.

### Sensor parser tests

- `test_parse_k10temp_tctl_temperature`
- `test_parse_amdgpu_edge_temperature`
- `test_parse_nvme_composite_temperature`
- `test_ignore_voltage_power_and_fan_values_initially`
- `test_parse_adapter_line`
- `test_malformed_lines_do_not_raise`

### Metrics tests

- `test_format_cpu_percent`
- `test_format_memory_used_percent`
- `test_missing_psutil_returns_unavailable`
- `test_missing_sensors_command_returns_unavailable`
- `test_configured_missing_sensor_is_skipped_or_na`

### History tests

- `test_history_capacity_default_is_60`
- `test_history_capacity_uses_interval_and_minutes`
- `test_history_buffer_drops_oldest_values`

## Manual GUI tests

- Introduce a YAML syntax error in `pvfclock2.yaml`; confirm the startup dialog and stderr identify the file, line, and column.
- Choose Exit and confirm the YAML is unchanged; restart and choose Run with defaults.
- Double-click the clock in temporary-defaults mode; confirm saving is disabled and the YAML is unchanged.
- Fix the YAML and press `Ctrl+R`; confirm normal configuration and geometry saving are restored.

- Start app with no `~/.config/pvfclock2.yaml`.
- Confirm default YAML is created.
- Confirm productive `~/.config/pvfclock.conf` timestamp is unchanged.
- Confirm clock appears as before.
- Right click, confirm `Toggle Monitor` appears.
- Press `Ctrl+1`, panel appears below clock.
- Move clock, panel follows.
- Press `Ctrl+1`, panel hides.
- Double click status/date with panel hidden, calendar opens below clock.
- Open panel, double click status/date, calendar opens below panel.
- Disable a metric in YAML, restart, confirm it is hidden.
- Rename a metric label in YAML, restart, confirm new label appears.
- Temporarily make `sensors` unavailable, confirm app still starts.
- Configure a slow sensor command and confirm the clock, dragging, and monitor toggle remain responsive.
- Quit during slow collection using both `Ctrl+Q` and window close; confirm the app exits after collection finishes without thread warnings.

## Asynchronous polling tests

`tests/test_async_monitor.py` verifies:

- A GUI heartbeat continues while collection is blocked in the worker thread.
- Widget updates run on the GUI thread, and collections never overlap.
- Timer ticks skip busy collection; explicit refresh requests coalesce.
- Collection and display exceptions are logged and later polls recover.
- Reloaded config is isolated from active work, stale results are discarded, and external-IP refresh intent survives.
- History collection respects hidden-panel settings.
- Shutdown discards late results and pending work, including real window-close and `Ctrl+Q` paths.

For headless validation, run `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest`.
Slow collection delays fresh monitor values; shutdown waits asynchronously for active collection to finish.

## Test command

```bash
python -m pytest
```

## Static sanity command

```bash
python -m compileall .
```
