# Codex Test Plan

## Automated tests

Create tests under `tests/` for pure Python logic.

### Config tests

- `test_default_config_path_is_pvfclock2_yaml`
- `test_default_config_is_written_when_missing`
- `test_existing_user_values_are_preserved_on_merge`
- `test_legacy_config_path_is_never_used`

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

## Test command

```bash
python -m pytest
```

## Static sanity command

```bash
python -m compileall .
```
