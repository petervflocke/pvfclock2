# Codex Review Checklist

## Safety

- [ ] No code reads or writes `~/.config/pvfclock.conf`.
- [ ] New config path is `~/.config/pvfclock2.yaml`.
- [ ] Existing clock behavior is preserved.
- [ ] Missing optional dependencies do not crash the app.
- [ ] `sensors` execution has a timeout.

## Architecture

- [ ] Monitor panel is a separate window.
- [ ] Parser code is separate from command execution.
- [ ] Metrics collection is separate from UI rendering.
- [ ] History buffer logic is bounded.
- [ ] Sparklines do not add plotting dependencies.

## Config

- [ ] Defaults are readable YAML.
- [ ] Missing defaults merge into existing YAML.
- [ ] User values are preserved.
- [ ] Labels, enablement, graph flags, interval, and history are configurable.

## UI

- [ ] `Ctrl+1` toggles monitor panel.
- [ ] Right click menu includes monitor toggle.
- [ ] `Ctrl+Q` still quits.
- [ ] Panel opens below clock.
- [ ] Panel follows clock movement.
- [ ] Scroll area works with additional sensors.
- [ ] Calendar placement accounts for visible panel.

## Tests and validation

- [ ] Sensor parser tests exist.
- [ ] Config tests exist.
- [ ] History tests exist.
- [ ] `python -m compileall .` passes.
- [ ] `python -m pytest` passes or missing tooling is explained.
