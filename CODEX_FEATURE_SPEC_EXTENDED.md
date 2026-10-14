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

## Alarm extension contracts

The approved alarm extension in `CODEX_FEATURE_SPEC.md` is the source of truth.
Alarm state belongs in the main YAML, not a separate persistence file.

Suggested focused modules:

- `alarm_model.py`: typed dataclass/enum for a single alarm record; pure validation,
  timezone conversion, due/missed decisions, and explicit state transitions.
- `alarm_controller.py`: lightweight independent Qt timer, startup reconciliation,
  set/cancel/claim orchestration, and signals for status/notification. Inject time
  and persistence for deterministic tests; do not tie alarm checks to sensor polls.
- `alarm_panel.py`: keyboard-first editor and status UI; no persistence or due-time
  decisions in widget code.
- `alarm_notification.py`: notification, bounded nonblocking audio, dismissal, and
  cleanup. Select and validate a Qt-compatible audio backend/bundled asset during
  implementation; document any dependency and license. Audio failure must retain
  the visible notification without rearming the alarm.
- `AppConfig`: shared atomic, coordinated YAML mutations for ALL writers, including
  geometry/default merges. Read fresh state under a runtime lock, validate the
  expected alarm ID/state, write a sibling temporary file, flush/fsync and replace
  atomically before acknowledging a fired claim. Release locks and clean temporary
  files on failures. Do not use a lock on a YAML inode replaced during the write.
- `MainWindow`: Ctrl+2/menu action, bell/status indicator, stack docking, and calendar
  anchoring. Keep the clock itself at its existing geometry.

Do not hold a lock or perform potentially lengthy persistence work on the GUI
thread. Serialize mutations and return completion signals before activating audio.
An alarm claim succeeds only if the persisted record still has the expected ID and
`armed` state. Reread state before writes so multiple instances and stale snapshots
cannot duplicate or resurrect an alarm. Reconcile external transitions for status.

At startup any past armed alarm becomes missed, without a grace-period ring.
While running, apply the 10-second tolerance; startup and running evaluation are
separate testable paths. No alarm timer or state reload may replay terminal states.
Only explicit set/replacement creates a fresh ID. Defaults/reset may clear to null;
normal merges and preference saves must preserve current persisted state.

Keep temporary-default mode read-only and empty of alarms. Explain disabled arming
in the UI until configuration is writable. Report malformed alarm data without
silently rewriting it. Full unrelated preference validation remains separate.

The extension is not complete until model, persistence, concurrency, UI stacking,
restart/missed-alarm, and notification cleanup tests pass. Desktop audio and
window-manager behavior require manual acceptance as well.

Implementation note: `alarm_store.py` owns record transactions; `config_storage.py`
provides shared runtime locking and atomic YAML writes. Geometry saves and config
reloads use the alarm storage worker. The included synthesized WAV uses
QtMultimedia QSoundEffect, with a visible fallback when audio is unavailable.
