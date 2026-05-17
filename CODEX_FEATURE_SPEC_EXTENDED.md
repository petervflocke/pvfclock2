# pvfclock2 Codex Feature Spec Extension

This file extends `CODEX_FEATURE_SPEC.md` with engineering definitions that make the implementation safer for Codex and easier to review.

## Source of truth

Primary product spec: `CODEX_FEATURE_SPEC.md`.

This extension defines implementation contracts, test expectations, file boundaries, review gates, and prompt structure. Product behavior conflicts must be resolved in favor of `CODEX_FEATURE_SPEC.md` unless this file is explicitly updated.

## Repository safety rule

The productive app configuration is out of scope and must remain untouched.

Forbidden path:

```text
~/.config/pvfclock.conf
```

Required path:

```text
~/.config/pvfclock2.yaml
```

Implementation must not import legacy config constants that write to the forbidden path.

## Suggested module contracts

### `app_config.py`

Responsibilities:

- Define immutable defaults.
- Resolve config path with `Path.home() / ".config" / "pvfclock2.yaml"`.
- Load YAML safely with `yaml.safe_load`.
- Create parent directory if missing.
- Create default file if missing.
- Deep merge defaults into loaded user config.
- Preserve user values when adding new default keys.
- Provide helper getters for clock, panel, metrics, colors.

Public API proposal:

```python
class AppConfig:
    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig": ...
    def save(self) -> None: ...
    def get(self, dotted_key: str, default: object | None = None) -> object: ...
    @property
    def data(self) -> dict[str, object]: ...
```

### `sensors_parser.py`

Responsibilities:

- Parse text only. Do not execute commands.
- Return structured readings grouped by chip and feature.
- Accept temperatures with `°C` and values such as `+49.9°C`.
- Preserve original chip and feature names exactly.
- Ignore non-temperature readings in first implementation.

Data model proposal:

```python
@dataclass(frozen=True)
class SensorReading:
    chip: str
    adapter: str | None
    feature: str
    value: float
    unit: str
```

Public API proposal:

```python
def parse_sensors_output(output: str) -> list[SensorReading]: ...
```

### `metrics_provider.py`

Responsibilities:

- Collect system load, CPU, memory, temperatures.
- Convert missing dependencies or commands into unavailable values.
- No direct Qt widget updates.

Data model proposal:

```python
@dataclass(frozen=True)
class MetricValue:
    key: str
    label: str
    value: float | None
    display_value: str
    unit: str
    available: bool
```

### `monitor_controller.py`

Responsibilities:

- Own `QTimer` polling.
- Maintain bounded history buffers.
- Respect `collect_history.mode`.
- Push formatted values to `MonitorPanel`.

### `monitor_panel.py`

Responsibilities:

- Draw the panel shell and metric rows.
- Expose methods to set metric values and history.
- Keep layout scrollable.
- Never collect metrics directly.

### `sparkline_widget.py`

Responsibilities:

- Paint a compact line graph from a list of numeric values.
- Handle empty or single value data gracefully.
- Use configured colors.

## Implementation order

1. Add config foundation and tests.
2. Add pure sensor parser and tests.
3. Add metric provider without UI wiring.
4. Add panel shell and toggle action.
5. Add controller polling and UI updates.
6. Add history buffers and sparklines.
7. Adjust calendar positioning.
8. Run acceptance checklist.

## Error handling contract

| Situation | Expected behavior |
| --- | --- |
| Config YAML missing | Create default config file |
| Config YAML partially outdated | Merge missing default keys |
| Config YAML invalid | Start with defaults and keep a backup or clear error message |
| `psutil` missing | App starts, CPU and memory show unavailable |
| `sensors` missing | App starts, temperatures hidden or unavailable |
| Configured sensor not present | App starts, reading hidden or `n/a` depending on config |
| Polling exception | Current tick fails safely, next tick continues |

## Test matrix

| Area | Automated | Manual |
| --- | --- | --- |
| Config path isolation | yes | yes |
| Default config merge | yes | no |
| Sensor parsing | yes | no |
| Metric formatting | yes | no |
| Panel toggle | optional | yes |
| Panel follows clock | optional | yes |
| Calendar placement | optional | yes |
| Missing dependencies | yes where practical | yes |

## Definition of Done

- All acceptance criteria in `CODEX_FEATURE_SPEC.md` are satisfied.
- Existing clock behavior is preserved.
- New config path is used exclusively.
- New non-Qt logic has tests.
- `python -m compileall .` succeeds.
- `python -m pytest` succeeds, or missing test tooling is documented.
- Final response includes changed files, tests run, and any known limitations.
