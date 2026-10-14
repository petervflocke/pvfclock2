# Digital Clock on pyQt5

Just replacing an old dclock with my python version.
I need a big clock in the upper right corner of my second monitor.

Configuration is stored in `~/.config/pvfclock2.yaml`. If YAML syntax is invalid,
startup reports the file, line, and column in the terminal and a dialog. Choose
**Exit** to fix it first, or **Run with defaults** to use temporary settings.
Temporary settings never overwrite the file; geometry saving is disabled until
you fix the YAML and use **Reload Config** (`Ctrl+R`). A failed reload keeps the
current configuration active. The document must contain a YAML mapping; validation
of every individual configuration value is not yet implemented.

## One-time alarm

Press **Ctrl+2** (or right-click → Toggle Alarm). Type `1430` or `14:30`, choose
an optional date and label, then press Enter or Set alarm. Hours/minutes support
Left/Right selection, Up/Down, mouse buttons, and the mouse wheel when focused.
A time already passed today suggests tomorrow; check the full date in the preview.
Escape hides unconfirmed edits. Hiding the panel does not cancel the alarm.
Use Cancel alarm to cancel it; setting another replaces the one active alarm.

The alarm panel sits directly below the clock and above the monitor. The calendar
follows the bottom of the visible stack. An armed alarm shows a bell/time on the
clock; the panel keeps the latest fired/cancelled/missed status.

Alarms only work while this app is running. A future alarm survives restart; an
alarm already past at startup expires silently. While running, a delay of up to
10 seconds is tolerated; longer delays (including sleep) expire silently. There
is no background scheduler, wakeup, snooze, or recurrence.

On activation a popup appears, the clock indicator flashes, and an included tone
plays for up to 30 seconds. Enter/Escape in the popup dismiss it. Set
`alarm.sound.enabled: false` to silence the sound. Audio uses PyQt5 QtMultimedia;
if unavailable, the visible notification remains. Test audio on your desktop.

All alarm data is stored under `alarm` in `~/.config/pvfclock2.yaml`. Do not edit
an alarm record to rearm it: use Set alarm to create a new ID. A reset of the YAML
to defaults clears the alarm. Temporary-default mode cannot arm or save alarms.
Runtime lock files contain no alarm/configuration data.

The app records an alarm as fired **before** starting sound or notification, so a
restart or second instance cannot repeat it. A crash between that save and the
notification can lose the notification. This deliberately favors at-most-once
activation. A persistence error prevents notification and is shown in alarm status.
