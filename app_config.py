from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path.home() / ".config" / "pvfclock2.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "config_version": 1,
        "reload_shortcut": "Ctrl+R",
        "update_interval_seconds": 5,
        "collect_history": {
            "mode": "always",
            "history_minutes": 5,
        },
    },
    "clock": {
        "geometry": {
            "x": 2250,
            "y": 40,
            "w": 300,
            "h": 140,
        },
        "colors": {
            "lcd_back": "#006400",
            "lcd_face": "#7fff00",
            "clock_back": "#2f4f4f",
            "panel_back": "#1f2929",
            "panel_text": "#d8ffd0",
            "panel_muted": "#7fa37f",
            "graph_line": "#7fff00",
            "graph_grid": "#5f6b6b",
        },
        "icon": "/usr/share/icons/hicolor/scalable/apps/org.gnome.clocks.svg",
    },
    "monitor_panel": {
        "enabled": True,
        "shortcut": "Ctrl+1",
        "height_mode": "fixed",
        "height": 260,
        "min_height": 120,
        "max_height": 600,
        "width_mode": "clock",
        "fixed_width": 360,
        "scroll": True,
    },
    "metrics": {
        "system_load": {
            "enabled": True,
            "label": "System Load",
            "source": "os.getloadavg",
            "display": "1m",
            "graph": {"enabled": True},
            "text": {"enabled": False},
            "alarm": {"max": None, "color": "#ff5555"},
        },
        "cpu": {
            "enabled": True,
            "label": "CPU",
            "source": "psutil.cpu_percent",
            "graph": {"enabled": True},
            "text": {"enabled": False},
            "alarm": {"max": 90, "color": "#ff5555"},
        },
        "memory": {
            "enabled": True,
            "label": "Memory",
            "mode": "used_percent",
            "graph": {"enabled": True},
            "text": {"enabled": False},
            "alarm": {"max": 90, "color": "#ff5555"},
        },
        "temperatures": {
            "enabled": True,
            "command": "sensors",
            "graph": {"enabled": True},
            "chips": {
                "k10temp-pci-00c3": {
                    "enabled": True,
                    "label": "CPU",
                    "features": {
                        "Tctl": {
                            "enabled": True,
                            "label": "CPU",
                            "graph": {"enabled": True},
                            "text": {"enabled": False},
                            "alarm": {"max": None, "color": "#ff5555"},
                        },
                    },
                },
                "amdgpu-pci-c400": {
                    "enabled": True,
                    "label": "GPU",
                    "features": {
                        "edge": {
                            "enabled": True,
                            "label": "GPU",
                            "graph": {"enabled": True},
                            "text": {"enabled": False},
                            "alarm": {"max": None, "color": "#ff5555"},
                        },
                    },
                },
                "nvme-pci-0300": {
                    "enabled": True,
                    "label": "NVMe",
                    "features": {
                        "Composite": {
                            "enabled": True,
                            "label": "NVMe",
                            "graph": {"enabled": True},
                            "text": {"enabled": False},
                            "alarm": {"max": None, "color": "#ff5555"},
                        },
                    },
                },
            },
        },
        "network": {
            "enabled": False,
            "interfaces": {},
        },
    },
}


def _deep_merge(defaults: dict[str, Any], loaded: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if not loaded:
        return deepcopy(defaults), bool(defaults)

    merged: dict[str, Any] = {}
    changed = False
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(defaults.get(key), dict):
            merged[key], nested_changed = _deep_merge(defaults[key], value)
            changed = changed or nested_changed
        else:
            merged[key] = deepcopy(value)

    for key, value in defaults.items():
        if key not in merged:
            merged[key] = deepcopy(value)
            changed = True

    return merged, changed


class AppConfig:
    def __init__(self, path: Path, data: dict[str, Any]):
        self.path = path
        self._data = data

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        config_path = path or CONFIG_PATH
        loaded: dict[str, Any] = {}
        missing_config = not config_path.exists()

        if not missing_config:
            with config_path.open("r", encoding="utf-8") as config_file:
                raw = yaml.safe_load(config_file) or {}
            if isinstance(raw, dict):
                loaded = raw

        data, changed = _deep_merge(DEFAULT_CONFIG, loaded)
        changed = _merge_metric_display_defaults(data, loaded) or changed
        changed = _merge_temperature_feature_defaults(data, loaded) or changed
        changed = _merge_network_feature_defaults(data, loaded) or changed
        config = cls(config_path, data)
        if missing_config or changed:
            config.save()
        return config

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def get(self, dotted_key: str, default: object | None = None) -> object:
        current: object = self._data
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as config_file:
            yaml.safe_dump(self._data, config_file, sort_keys=False)

    def clock_params(self) -> dict[str, Any]:
        geometry = self.get("clock.geometry", {})
        colors = self.get("clock.colors", {})
        return {
            "x": int(self._dict_get(geometry, "x", DEFAULT_CONFIG["clock"]["geometry"]["x"])),
            "y": int(self._dict_get(geometry, "y", DEFAULT_CONFIG["clock"]["geometry"]["y"])),
            "w": int(self._dict_get(geometry, "w", DEFAULT_CONFIG["clock"]["geometry"]["w"])),
            "h": int(self._dict_get(geometry, "h", DEFAULT_CONFIG["clock"]["geometry"]["h"])),
            "lcd_back": str(self._dict_get(colors, "lcd_back", DEFAULT_CONFIG["clock"]["colors"]["lcd_back"])),
            "lcd_face": str(self._dict_get(colors, "lcd_face", DEFAULT_CONFIG["clock"]["colors"]["lcd_face"])),
            "clock_back": str(
                self._dict_get(colors, "clock_back", DEFAULT_CONFIG["clock"]["colors"]["clock_back"])
            ),
            "icon": str(self.get("clock.icon", DEFAULT_CONFIG["clock"]["icon"])),
        }

    def update_clock_params(self, params: dict[str, Any]) -> None:
        self._data["clock"]["geometry"].update(
            {
                "x": int(params["x"]),
                "y": int(params["y"]),
                "w": int(params["w"]),
                "h": int(params["h"]),
            }
        )
        self._data["clock"]["colors"].update(
            {
                "lcd_back": str(params["lcd_back"]),
                "lcd_face": str(params["lcd_face"]),
                "clock_back": str(params["clock_back"]),
            }
        )
        self._data["clock"]["icon"] = str(params["icon"])
        self.save()

    @staticmethod
    def _dict_get(value: object, key: str, default: object) -> object:
        if isinstance(value, dict):
            return value.get(key, default)
        return default


def _merge_temperature_feature_defaults(data: dict[str, Any], loaded: dict[str, Any] | None = None) -> bool:
    changed = False
    chips = (
        data.get("metrics", {})
        .get("temperatures", {})
        .get("chips", {})
    )
    loaded_chips = {}
    if isinstance(loaded, dict):
        loaded_chips = (
            loaded.get("metrics", {})
            .get("temperatures", {})
            .get("chips", {})
        )
        if not isinstance(loaded_chips, dict):
            loaded_chips = {}
    if not isinstance(chips, dict):
        return changed

    for chip_name, chip_config in chips.items():
        if not isinstance(chip_config, dict):
            continue
        features = chip_config.get("features", {})
        if not isinstance(features, dict):
            continue
        loaded_chip = loaded_chips.get(chip_name, {}) if isinstance(loaded_chips, dict) else {}
        loaded_features = loaded_chip.get("features", {}) if isinstance(loaded_chip, dict) else {}
        if not isinstance(loaded_features, dict):
            loaded_features = {}
        for feature_name, feature_config in features.items():
            if not isinstance(feature_config, dict):
                continue
            loaded_feature = loaded_features.get(feature_name, {})
            loaded_has_text = isinstance(loaded_feature, dict) and "text" in loaded_feature
            if "graph" not in feature_config:
                feature_config["graph"] = {"enabled": True}
                changed = True
            if not loaded_has_text:
                feature_config["text"] = {"enabled": not _display_enabled(feature_config.get("graph"), True)}
                changed = True
            if "alarm" not in feature_config:
                feature_config["alarm"] = {"max": None, "color": "#ff5555"}
                changed = True
    return changed


def _merge_metric_display_defaults(data: dict[str, Any], loaded: dict[str, Any]) -> bool:
    changed = False
    metrics = data.get("metrics", {})
    loaded_metrics = loaded.get("metrics", {}) if isinstance(loaded.get("metrics"), dict) else {}
    if not isinstance(metrics, dict):
        return changed

    for metric_name in ("system_load", "cpu", "memory"):
        metric_config = metrics.get(metric_name, {})
        if not isinstance(metric_config, dict):
            continue
        loaded_metric = loaded_metrics.get(metric_name, {}) if isinstance(loaded_metrics, dict) else {}
        loaded_has_text = isinstance(loaded_metric, dict) and "text" in loaded_metric
        if not loaded_has_text:
            metric_config["text"] = {"enabled": not _display_enabled(metric_config.get("graph"), True)}
            changed = True
    return changed


def _merge_network_feature_defaults(data: dict[str, Any], loaded: dict[str, Any] | None = None) -> bool:
    changed = False
    interfaces = (
        data.get("metrics", {})
        .get("network", {})
        .get("interfaces", {})
    )
    loaded_interfaces = {}
    if isinstance(loaded, dict):
        loaded_interfaces = (
            loaded.get("metrics", {})
            .get("network", {})
            .get("interfaces", {})
        )
        if not isinstance(loaded_interfaces, dict):
            loaded_interfaces = {}
    if not isinstance(interfaces, dict):
        return changed

    for interface_name, interface_config in interfaces.items():
        if not isinstance(interface_config, dict):
            continue
        features = interface_config.get("features", {})
        if not isinstance(features, dict):
            continue
        loaded_interface = loaded_interfaces.get(interface_name, {}) if isinstance(loaded_interfaces, dict) else {}
        loaded_features = loaded_interface.get("features", {}) if isinstance(loaded_interface, dict) else {}
        if not isinstance(loaded_features, dict):
            loaded_features = {}
        for feature_name, feature_config in features.items():
            if not isinstance(feature_config, dict):
                continue
            loaded_feature = loaded_features.get(feature_name, {})
            loaded_has_text = isinstance(loaded_feature, dict) and "text" in loaded_feature
            if "graph" not in feature_config:
                feature_config["graph"] = {"enabled": True}
                changed = True
            if not loaded_has_text:
                feature_config["text"] = {"enabled": not _display_enabled(feature_config.get("graph"), True)}
                changed = True
            if "alarm" not in feature_config:
                feature_config["alarm"] = {"max": None, "color": "#ff5555"}
                changed = True
    return changed


def _display_enabled(config: object, default: bool) -> bool:
    if isinstance(config, dict) and "enabled" in config:
        return bool(config["enabled"])
    return default
