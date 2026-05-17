# AGENTS.md

## Mission

Implement the `pvfclock2` fold-down system monitor feature safely and incrementally. Treat `CODEX_FEATURE_SPEC.md` as the product source of truth.

This repository is a copy of the productive desktop clock app. Never read from or write to `~/.config/pvfclock.conf`. All new configuration must use `~/.config/pvfclock2.yaml`.

## Project context

- Runtime: Python 3, PyQt5 desktop app.
- Main entry point: `digitalclock.py`.
- Existing config helper: `config.py`.
- Calendar popup: `mycalendar.py`.
- New dependencies: `PyYAML`, `psutil`.
- Optional system command: `sensors` from lm-sensors.

## Non-negotiable constraints

- Keep the existing clock behavior working.
- Keep `Ctrl+Q` as quit.
- Add `Ctrl+1` as monitor toggle.
- Use a separate frameless monitor panel window docked below the clock. Do not resize the clock window to contain the panel.
- Avoid hardcoded sensor names in parser logic. Sensor enablement is driven by YAML config.
- Missing `psutil`, missing `sensors`, or missing configured sensors must not crash the app.
- Keep the first implementation small. No process list, network, disk, fan, voltage, power, packaging, autostart, or config migration.

## Preferred implementation shape

Use cohesive classes with limited responsibilities:

- `AppConfig`: load defaults, create YAML if missing, merge missing defaults into existing config, save user edited values safely.
- `MainWindow`: existing clock UI, actions, geometry persistence, menu, calendar trigger.
- `MonitorPanel`: frameless panel window, scroll area, metric rows, sparkline widgets.
- `MonitorController`: timer, polling cadence, history buffers, UI update orchestration.
- `SystemMetricsProvider`: system load, CPU, memory, temperature collection.
- `SensorsParser`: pure parsing of `sensors` output into structured readings.
- `SparklineWidget`: small custom Qt paint widget. Avoid plotting dependencies.

Prefer adding focused files if the current `digitalclock.py` is already large:

```text
app_config.py
monitor_panel.py
monitor_controller.py
metrics_provider.py
sensors_parser.py
sparkline_widget.py
```

Only keep code in `digitalclock.py` when doing so avoids risky churn.

## Coding rules

- Prefer simple, explicit Python over clever abstractions.
- Use type hints for new public functions and data containers.
- Use dataclasses for structured metric and sensor readings.
- Keep UI code and parsing code separate.
- Avoid blocking the Qt UI thread for long operations.
- Run `psutil.cpu_percent(interval=None)`, not a blocking interval call.
- Use `subprocess.run(..., capture_output=True, text=True, timeout=...)` for `sensors`.
- Use `pathlib.Path` for paths.
- Do not swallow exceptions silently. Convert expected failures into unavailable metric states.
- Keep styles centralized enough that colors come from config.

## Testing expectations

Add tests where practical, especially for non-Qt logic:

- default config creation and merge behavior
- config path isolation from `~/.config/pvfclock.conf`
- sensor parser examples with CPU, GPU, NVMe readings
- missing or malformed sensor lines
- history buffer max sample calculation
- metric formatting for load, CPU, memory, temperature

Qt GUI behavior may be verified manually if automated GUI testing is too heavy for this project.

## Commands

Use the commands available in the repository. If files are missing, create or update them as part of the change.

Recommended development flow:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest
python digitalclock.py
```

Recommended checks before final response:

```bash
python -m compileall .
python -m pytest
```

## Manual acceptance checklist

- `python digitalclock.py` starts the clock.
- `~/.config/pvfclock2.yaml` is created if missing.
- `~/.config/pvfclock.conf` is not touched.
- Right click menu contains `Toggle Monitor` and quit.
- `Ctrl+1` shows and hides the panel.
- Panel appears below the clock and follows movement.
- Calendar opens below the correct visible component.
- CPU, memory, load, and enabled temperatures render or show unavailable without crashing.
- Graph visibility follows YAML config.
