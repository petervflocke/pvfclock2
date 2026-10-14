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
