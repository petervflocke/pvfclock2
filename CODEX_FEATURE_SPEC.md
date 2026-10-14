# pvfclock2 Feature Spec: Fold-Down System Monitor

## Purpose

Extend the current PyQt5 desktop clock into a small always-on-top clock plus an optional fold-down monitoring panel. The app should stay close to the existing setup: Python, PyQt5, local virtualenv, simple desktop utility behavior, and user-editable configuration.

This repository is a copy of the productive desktop app. All new work must use a separate config path so it cannot interfere with the current productive app.

## Current Baseline

- Main entry point: `digitalclock.py`
- Config helper: `config.py`
- Calendar popup: `mycalendar.py`
- GUI toolkit: PyQt5
- Existing config path: `~/.config/pvfclock.conf`
- New config path required for this repo: `~/.config/pvfclock2.yaml`
- Current clock behavior:
  - frameless always-on-top clock window
  - LCD-style time display
  - date/status text in the status bar
  - drag window with mouse
  - double-click clock to save geometry
  - right-click context menu with `Ctrl+Q` exit action
  - date/status double-click opens calendar

## Product Goal

Add a keyboard-toggleable monitoring area inspired by Vitals and GKrellM: compact, readable, configurable, and useful at a glance. Start simple, with CPU/load/memory/temperature. Build the structure so later metrics can be added without rewriting the UI.

Vitals reference: https://github.com/corecoding/Vitals

## Architecture Decision

Use a second frameless panel window docked under the main clock window.

Do not resize the main clock window to contain the monitor panel.

Reasoning:

- The clock should remain stable and keep its current geometry/persistence behavior.
- The monitor panel can be shown/hidden without disturbing clock layout.
- The panel can have its own height, scroll area, history graphs, and content rules.
- The panel can be glued to the clock by syncing position and width whenever the clock moves or resizes.
- This keeps future features such as calendar embedding, graphs, and scrollable metric groups isolated from the clock display.

Recommended object model:

- `MainWindow`: existing clock window; owns actions and geometry persistence.
- `MonitorPanel`: new frameless QWidget/QFrame/QMainWindow shown below `MainWindow`.
- `MonitorController`: coordinates polling, history buffers, and UI updates.
- `SystemMetricsProvider`: reads CPU load, system load, memory, and temperature.
- `SensorsParser`: parses `sensors` command output into structured chip/feature readings.
- `AppConfig`: loads/saves YAML config and supplies defaults.

## Keyboard And Menu Behavior

Add a new action:

- Label: `Toggle Monitor`
- Shortcut: `Ctrl+1`
- Behavior:
  - if monitor panel is hidden, show it
  - if monitor panel is visible, hide it

Keep existing action:

- `Ctrl+Q`: quit app

The monitor toggle action should also appear in the right-click context menu, alongside exit.

## Window Behavior

Main clock:

- Stays frameless and always-on-top.
- Keeps current drag behavior.
- Keeps current geometry save behavior.

Monitor panel:

- Frameless.
- Always-on-top, same stacking intent as the clock.
- Opens directly below the main clock.
- X coordinate equals main clock X.
- Y coordinate equals main clock Y + main clock height.
- Default width equals main clock width.
- Height comes from config, with sensible min/max.
- Contains a vertical scroll area if content does not fit.
- Should move with the clock while visible.
- Should resize/reposition when the clock is resized.
- Should hide on `Ctrl+1` if already visible.

Initial visual style:

- Dark background consistent with the existing clock.
- Compact rows.
- No heavy decoration.
- Metric labels left, values right.
- Optional small graph/sparkline below rows when enabled.

## Calendar Behavior

Keep the existing date/status double-click calendar behavior for now, but prepare it for the new panel layout.

Future-compatible decision:

- Calendar remains a separate widget initially.
- Calendar positioning should account for the monitor panel:
  - if monitor panel is closed, calendar opens below the clock
  - if monitor panel is open, calendar opens below the monitor panel or uses a configured position mode
- Calendar size/style should be made configurable later if it is embedded into the monitor panel.

Do not merge the calendar into the monitor panel in the first implementation unless explicitly requested later.

## Config Format

Use YAML for the new configuration.

New file:

```text
~/.config/pvfclock2.yaml
```

Do not read or write:

```text
~/.config/pvfclock.conf
```

Add dependency:

```text
PyYAML
```

Recommended optional dependency:

```text
psutil
```

`psutil` should be used for CPU and memory metrics unless the user later requests a standard-library-only implementation.

## Config Principles

The config should expose all user-visible monitor content with:

- `enabled`: on/off
- `label`: alias/name displayed on screen
- `graph.enabled`: on/off where graphing is supported
- polling/history settings
- sensor mapping by real chip/feature names

YAML should be readable and editable by hand.

The app should create the YAML file with defaults if missing.

If new options are added later, the app should merge defaults into the loaded config and preserve known user values.

## Example YAML Config

```yaml
app:
  config_version: 1
  update_interval_seconds: 5
  collect_history:
    mode: always        # always | panel_visible
    history_minutes: 5

clock:
  geometry:
    x: 2250
    y: 40
    w: 300
    h: 140
  colors:
    lcd_back: "#006400"
    lcd_face: "#7fff00"
    clock_back: "#2f4f4f"
    panel_back: "#1f2929"
    panel_text: "#d8ffd0"
    panel_muted: "#7fa37f"
    graph_line: "#7fff00"
  icon: "/usr/share/icons/hicolor/scalable/apps/org.gnome.clocks.svg"

monitor_panel:
  enabled: true
  shortcut: "Ctrl+1"
  height: 260
  min_height: 120
  max_height: 600
  width_mode: clock     # clock | fixed
  fixed_width: 360
  scroll: true

metrics:
  system_load:
    enabled: true
    label: "System Load"
    source: "os.getloadavg"
    display: "1m"
    graph:
      enabled: true

  cpu:
    enabled: true
    label: "CPU"
    source: "psutil.cpu_percent"
    graph:
      enabled: true

  memory:
    enabled: true
    label: "Memory"
    mode: "used_percent"   # used_percent | available | used
    graph:
      enabled: true

  temperatures:
    enabled: true
    command: "sensors"
    graph:
      enabled: true
    chips:
      iwlwifi_1-virtual-0:
        enabled: false
        label: "Wi-Fi"
        features:
          temp1:
            enabled: false
            label: "Wi-Fi"

      spd5118-i2c-16-50:
        enabled: false
        label: "Memory DIMM 1"
        features:
          temp1:
            enabled: false
            label: "DIMM 1"

      r8169_0_100:00-mdio-0:
        enabled: false
        label: "Ethernet"
        features:
          temp1:
            enabled: false
            label: "Ethernet"

      amdgpu-pci-c400:
        enabled: true
        label: "GPU"
        features:
          edge:
            enabled: true
            label: "GPU"

      acpitz-acpi-0:
        enabled: false
        label: "Motherboard"
        features:
          temp1:
            enabled: false
            label: "Motherboard"

      spd5118-i2c-16-51:
        enabled: false
        label: "Memory DIMM 2"
        features:
          temp1:
            enabled: false
            label: "DIMM 2"

      k10temp-pci-00c3:
        enabled: true
        label: "CPU"
        features:
          Tctl:
            enabled: true
            label: "CPU"

      nvme-pci-0300:
        enabled: true
        label: "NVMe"
        features:
          Composite:
            enabled: true
            label: "NVMe"
          Sensor 1:
            enabled: false
            label: "NVMe Sensor 1"
          Sensor 2:
            enabled: false
            label: "NVMe Sensor 2"
```

## Sensor Parsing Requirement

Implement dynamic parsing of the `sensors` command output.

Do not hardwire the code to one motherboard.

The parser should identify:

- chip name, for example `k10temp-pci-00c3`
- adapter line, for example `Adapter: PCI adapter`
- feature name, for example `Tctl`, `Composite`, `edge`, `temp1`
- numeric value
- unit, for example `C`, `V`, `W`

For the first implementation, consume temperature readings only:

- values with `°C`
- output strings such as `+49.9°C`

Later, the same parser may support voltage, power, and fan speed.

The monitor should display only configured and enabled chip/feature pairs. Unknown sensors may be ignored, but a later debug/log mode can list them.

## Metrics To Implement First

1. System load
   - Source: `os.getloadavg()`
   - Display: 1-minute load average initially
   - Optional later display: 1m / 5m / 15m

2. CPU load
   - Source: `psutil.cpu_percent(interval=None)`
   - Display: percentage
   - Poll on configured interval

3. Memory
   - Source: `psutil.virtual_memory()`
   - Default display: used percent
   - Optional config display modes: available, used, used percent

4. Temperature
   - Source: `sensors` command
   - Parser maps configured chip/feature names to display aliases
   - Initial enabled defaults:
     - `k10temp-pci-00c3` / `Tctl` as `CPU`
     - `amdgpu-pci-c400` / `edge` as `GPU`
     - `nvme-pci-0300` / `Composite` as `NVMe`

## History And Graphs

Collect history for graphable metrics.

Default:

- update interval: 5 seconds
- history duration: 5 minutes
- samples retained per metric: `history_minutes * 60 / update_interval_seconds`
- with defaults: 60 samples

History collection mode:

- `always`: collect even when monitor panel is hidden
- `panel_visible`: collect only when monitor panel is visible

Initial graph style:

- simple sparkline line graph
- no axes required in first implementation
- fixed height per graph row, for example 28-40 px
- current value still shown as text

Preferred implementation:

- draw sparklines directly with Qt painting in a small custom widget
- avoid adding a plotting dependency unless the graph feature becomes more advanced

Graphs should be switchable per metric group using config.

## Layout Proposal For First Version

Inside monitor panel:

```text
System Load      0.72
[sparkline]

CPU              12%
[sparkline]

Memory           41%
[sparkline]

Temperatures
CPU              49.9 C
[sparkline]
GPU              42.0 C
[sparkline]
NVMe             33.9 C
[sparkline]
```

Use a `QScrollArea` so more sensors can be enabled without changing the panel architecture.

## Implementation Steps

Step 1: Config foundation

- Add YAML config support.
- Switch this repo to `~/.config/pvfclock2.yaml`.
- Preserve current clock defaults.
- Write defaults when missing.
- Merge missing default keys into existing YAML.

Step 2: Clean current clock code

- Remove duplicated `showTime()` logic.
- Fix status bar double-click signature.
- Remove duplicate stylesheet assignment.
- Keep one canonical clock file.
- Do not delete experimental files unless explicitly requested.

Step 3: Add monitor panel shell

- Add `MonitorPanel` class.
- Add `Ctrl+1` action.
- Dock panel below clock.
- Move/reposition panel with clock.
- Add scroll area and placeholder metric rows.

Step 4: Add metrics provider

- Add CPU, load, memory.
- Add `psutil` dependency.
- Poll every configured interval.
- Update visible metric rows.

Step 5: Add sensors parser

- Run `sensors`.
- Parse dynamic chip/feature temperature values.
- Map to YAML config aliases.
- Display enabled configured temperatures only.
- Handle missing `sensors` command gracefully.

Step 6: Add history and sparklines

- Keep rolling history buffers.
- Implement small custom Qt sparkline widget.
- Respect per-metric `graph.enabled`.
- Respect `collect_history.mode`.

Step 7: Calendar positioning adjustment

- If monitor panel is visible, open calendar under panel.
- If monitor panel is hidden, open calendar under clock.
- Keep calendar as separate popup for now.

## Error Handling

If `sensors` is missing:

- Do not crash.
- Show temperatures as unavailable or hide the temperature section.
- Optional status/log message: `sensors command not found`.

If a configured sensor is not present:

- Do not crash.
- Hide missing reading by default, or show `n/a` if a later config option requests it.

If `psutil` is missing:

- App should still start.
- CPU/memory sections should show unavailable.
- Development install should include `psutil` in `requirements.txt`.

## Requirements File Updates

Add:

```text
PyYAML
psutil
```

Keep PyQt5 pinned as currently configured unless dependency resolution requires a change.

## Non-Goals For First Implementation

- No full task manager/process list.
- No network throughput yet.
- No disk usage yet.
- No fan/voltage/power display yet, despite parser structure allowing later expansion.
- No packaging/autostart changes yet.
- No migration from productive `~/.config/pvfclock.conf`.

## Acceptance Criteria

- Running `digitalclock.py` creates/uses `~/.config/pvfclock2.yaml`.
- Productive config `~/.config/pvfclock.conf` is not touched.
- Clock still works as before.
- `Ctrl+Q` still quits.
- `Ctrl+1` toggles the monitor panel.
- Monitor panel appears directly below the clock and follows it when moved.
- Panel displays at least:
  - system load
  - CPU percentage
  - memory usage
  - configured temperatures from `sensors`
- User can enable/disable each content group in YAML.
- User can rename display labels in YAML.
- User can enable/disable graphs in YAML.
- History uses configured interval and duration.
- Missing sensors or missing commands do not crash the app.


## Approved extension: one-time alarm (implemented; desktop acceptance pending)

This extension adds one active alarm and takes precedence over earlier docking
rules where they differ. It does not authorize background scheduling, autostart,
recurrence, or additional configuration files.

### User interaction

- `Ctrl+2` and a `Toggle Alarm` context-menu action toggle a separate frameless,
  always-on-top alarm setup/status panel. `Ctrl+1` remains the monitor toggle;
  `Ctrl+Q` remains quit.
- Opening the panel focuses the time editor. Accept `14:30` and `1430`; Left/Right
  selects hour/minute segments, Up/Down changes them, and Tab moves between fields.
- Mouse input supports segment selection, increment/decrement arrows, and wheel
  changes over the selected time segment. Provide a date picker and optional label.
- Enter explicitly sets/replaces the alarm. Escape hides the editor without
  applying pending edits. Hiding the panel never cancels an armed alarm.
- A time already passed today suggests tomorrow. Show the full resolved date/time
  and time remaining before confirmation. Explicit past dates cannot be armed.
- Show the active alarm, last outcome, and a Cancel Alarm control. An edit takes
  effect only after Set Alarm; at most one alarm can be armed.
- Show a small bell and scheduled time on the main clock while armed.

### Panel order and calendar placement

All panels remain separate windows; do not resize the clock to contain them.
The vertical order is always clock, alarm panel (if visible), monitor (if visible).
The alarm panel opens directly below the clock, even when the monitor is already
open. Move the monitor below it immediately. Hiding the alarm moves the monitor
back directly below the clock. Visibility does not change alarm scheduling.

Align panel X coordinates to the clock. The alarm panel follows clock width;
retain the monitor's clock/fixed width setting. Recompute docking after toggles,
clock movement/resizing, and panel height changes. The calendar opens below the
lowest visible component (monitor, otherwise alarm, otherwise clock), retaining
the existing calendar gap. Reposition an already-visible calendar when the stack
changes as well. Keyboard focus and shortcuts must work across both panels.

### One-time and missed-alarm semantics

- Alarms activate only while the clock application is running. No OS scheduler,
  daemon, wake timer, background service, or wake-from-sleep behavior.
- Persist an absolute timezone-aware scheduled instant, plus the timezone used at
  entry for display. A timezone change keeps the original instant. Reject
  nonexistent daylight-saving times; clarify ambiguous times before arming.
- A future armed alarm survives normal exit/restart. If its due time has already
  passed at startup, mark it missed silently: no sound or popup, only status.
- During a running session, allow up to 10 seconds of lateness for normal timer
  delays. Beyond that, including a long suspension or forward clock jump, mark it
  missed silently. A short suspension within that tolerance can still ring.
- A backward clock change cannot reactivate a consumed alarm.
- States are `armed`, `fired`, `cancelled`, and `missed`; no alarm is represented by
  `current: null`. Only `armed` is eligible. Preserve the latest outcome for status
  until the user replaces or clears it.
- One activation may play sound repeatedly for at most 30 seconds or until
  dismissed. Show a visible notification with label/time and flash the clock's
  alarm indicator. Enter/Escape dismiss only when the notification has focus.
- Persist `fired` before notification or audio. Restarting after firing never
  repeats it, even if the notification was not dismissed. If persistence fails,
  report the error and do not sound. A crash after persistence but before sound
  can lose the notification: at-most-once activation is preferred to duplicates.
- Guard the transition against concurrent application instances. Only one may
  claim an armed alarm; stale configuration saves must never rearm it.

### Configuration and persistence

Use ONLY `~/.config/pvfclock2.yaml` for alarm preferences and state. Do not add an
alarm JSON/YAML file. An explicit reset to defaults may clear the alarm; preserving
an alarm across a user-requested reset is not required. Default merging must still
preserve an existing alarm. Temporary in-memory defaults start with no alarm and
retain their existing write protection: arming is unavailable until a valid config
is loaded or the user explicitly saves a default configuration. Do not silently
replace invalid YAML or remove the existing startup recovery dialog.

Proposed defaults:

```yaml
alarm:
  shortcut: "Ctrl+2"
  lateness_tolerance_seconds: 10
  sound:
    enabled: true
    duration_seconds: 30
  current: null
```

An active/current record contains `id` (unique per explicit set/replacement),
`scheduled_at` (UTC ISO-8601), `timezone` (entry timezone identifier), `label`,
`state`, and `state_changed_at` (UTC ISO-8601). A missing alarm section merges to
these defaults. An invalid alarm record must be reported and kept inactive; never
infer an armed alarm from malformed data.

All YAML writes, including geometry and default merging, must preserve the latest
alarm state through a shared atomic read/modify/write mechanism and interprocess
coordination. A transient lock in a runtime directory is permitted; it stores no
configuration or alarm data. Reload observes persisted transitions instead of
resurrecting stale in-memory records. State changes must not overwrite unrelated
user settings. Explicit default reset is the exception and clears the alarm.

### Scope and acceptance

First version: one alarm, keyboard/mouse time input, date, optional label,
set/replace/cancel, persistence, missed status, bounded sound, notification,
dismissal, and clock indicator. Snooze, recurrence, multiple alarms, presets,
custom sounds, background scheduling, and wakeup are future ideas, not current
requirements. If later added, snooze creates a new explicit one-time alarm.

Acceptance requires restart-safe at-most-once activation, silent missed alarms,
correct docking for all four alarm/monitor visibility combinations, responsive
clock behavior, keyboard completion without a mouse, and preservation of existing
monitor, calendar, YAML recovery, and quit behavior.
