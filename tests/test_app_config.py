from __future__ import annotations

from pathlib import Path

import yaml

import app_config
from app_config import AppConfig, DEFAULT_CONFIG


def test_default_config_path_is_pvfclock2_yaml() -> None:
    assert app_config.CONFIG_PATH == Path.home() / ".config" / "pvfclock2.yaml"


def test_default_config_is_written_when_missing(tmp_path: Path) -> None:
    config_path = tmp_path / ".config" / "pvfclock2.yaml"

    config = AppConfig.load(config_path)

    assert config_path.exists()
    assert config.data["clock"]["geometry"] == DEFAULT_CONFIG["clock"]["geometry"]
    written = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert written["clock"]["colors"]["lcd_face"] == "#7fff00"


def test_existing_user_values_are_preserved_on_merge(tmp_path: Path) -> None:
    config_path = tmp_path / ".config" / "pvfclock2.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
clock:
  geometry:
    x: 123
  colors:
    lcd_face: "#ffffff"
metrics:
  cpu:
    label: "Processor"
""".lstrip(),
        encoding="utf-8",
    )

    config = AppConfig.load(config_path)

    assert config.get("clock.geometry.x") == 123
    assert config.get("clock.geometry.y") == DEFAULT_CONFIG["clock"]["geometry"]["y"]
    assert config.get("clock.colors.lcd_face") == "#ffffff"
    assert config.get("clock.colors.clock_back") == DEFAULT_CONFIG["clock"]["colors"]["clock_back"]
    assert config.get("app.reload_shortcut") == "Ctrl+R"
    assert config.get("metrics.cpu.label") == "Processor"
    assert config.get("metrics.cpu.graph.enabled") is True
    assert config.get("metrics.cpu.text.enabled") is False
    assert config.get("metrics.cpu.alarm.max") == 90
    assert config.get("metrics.cpu.alarm.color") == "#ff5555"
    assert config.get("metrics.network.enabled") is False
    assert config.get("metrics.external_ip.enabled") is False
    assert config.get("metrics.external_ip.text.enabled") is True
    assert config.get("metrics.external_ip.refresh_seconds") == 3600
    assert config.get("metrics.temperatures.chips.k10temp-pci-00c3.features.Tctl.graph.enabled") is True
    assert config.get("metrics.temperatures.chips.k10temp-pci-00c3.features.Tctl.alarm.color") == "#ff5555"

    written = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert written["monitor_panel"]["shortcut"] == "Ctrl+1"
    assert written["monitor_panel"]["height_mode"] == "fixed"


def test_existing_user_sensor_order_is_preserved_on_merge(tmp_path: Path) -> None:
    config_path = tmp_path / ".config" / "pvfclock2.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
metrics:
  temperatures:
    chips:
      spd5118-i2c-16-50:
        enabled: true
        label: "DIMM 1"
        features:
          temp1:
            enabled: true
            label: "DIMM 1"
      k10temp-pci-00c3:
        enabled: true
        label: "CPU"
        features:
          Tctl:
            enabled: true
            label: "CPU"
""".lstrip(),
        encoding="utf-8",
    )

    config = AppConfig.load(config_path)

    chips = config.data["metrics"]["temperatures"]["chips"]
    assert list(chips)[:2] == ["spd5118-i2c-16-50", "k10temp-pci-00c3"]
    assert chips["spd5118-i2c-16-50"]["features"]["temp1"]["graph"]["enabled"] is True
    assert chips["spd5118-i2c-16-50"]["features"]["temp1"]["text"]["enabled"] is False
    assert chips["spd5118-i2c-16-50"]["features"]["temp1"]["alarm"] == {
        "max": None,
        "color": "#ff5555",
    }

    written = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert list(written["metrics"]["temperatures"]["chips"])[:2] == [
        "spd5118-i2c-16-50",
        "k10temp-pci-00c3",
    ]


def test_current_config_is_not_rewritten_when_no_defaults_are_missing(tmp_path: Path) -> None:
    config_path = tmp_path / ".config" / "pvfclock2.yaml"
    config = AppConfig.load(config_path)
    before = config_path.read_text(encoding="utf-8")
    before_mtime = config_path.stat().st_mtime_ns

    loaded_again = AppConfig.load(config_path)

    assert loaded_again.data == config.data
    assert config_path.read_text(encoding="utf-8") == before
    assert config_path.stat().st_mtime_ns == before_mtime


def test_outdated_config_is_rewritten_when_defaults_are_added(tmp_path: Path) -> None:
    config_path = tmp_path / ".config" / "pvfclock2.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
clock:
  colors:
    lcd_face: "#ffffff"
""".lstrip(),
        encoding="utf-8",
    )

    AppConfig.load(config_path)

    written = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert written["clock"]["colors"]["lcd_face"] == "#ffffff"
    assert written["clock"]["colors"]["graph_grid"] == "#5f6b6b"


def test_missing_text_display_defaults_to_true_when_graph_is_disabled(tmp_path: Path) -> None:
    config_path = tmp_path / ".config" / "pvfclock2.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
metrics:
  cpu:
    graph:
      enabled: false
  temperatures:
    chips:
      k10temp-pci-00c3:
        enabled: true
        label: "CPU"
        features:
          Tctl:
            enabled: true
            label: "CPU"
            graph:
              enabled: false
""".lstrip(),
        encoding="utf-8",
    )

    config = AppConfig.load(config_path)

    assert config.get("metrics.cpu.text.enabled") is True
    assert config.get("metrics.temperatures.chips.k10temp-pci-00c3.features.Tctl.text.enabled") is True


def test_network_feature_defaults_are_added(tmp_path: Path) -> None:
    config_path = tmp_path / ".config" / "pvfclock2.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        """
metrics:
  network:
    enabled: true
    interfaces:
      enp1s0:
        enabled: true
        label: LAN
        features:
          rx:
            enabled: true
            label: LAN RX
          tx:
            enabled: true
            label: LAN TX
            graph:
              enabled: false
""".lstrip(),
        encoding="utf-8",
    )

    config = AppConfig.load(config_path)

    assert config.get("metrics.network.interfaces.enp1s0.features.rx.graph.enabled") is True
    assert config.get("metrics.network.interfaces.enp1s0.features.rx.text.enabled") is False
    assert config.get("metrics.network.interfaces.enp1s0.features.rx.alarm.color") == "#ff5555"
    assert config.get("metrics.network.interfaces.enp1s0.features.tx.text.enabled") is True


def test_legacy_config_path_is_never_used_by_default_load(
    tmp_path: Path, monkeypatch
) -> None:
    legacy_path = tmp_path / ".config" / "pvfclock.conf"
    new_path = tmp_path / ".config" / "pvfclock2.yaml"
    legacy_path.parent.mkdir(parents=True)
    legacy_contents = "[Window]\nx = 999\n"
    legacy_path.write_text(legacy_contents, encoding="utf-8")
    monkeypatch.setattr(app_config, "CONFIG_PATH", new_path)

    config = AppConfig.load()

    assert config.path == new_path
    assert new_path.exists()
    assert legacy_path.read_text(encoding="utf-8") == legacy_contents
    assert config.get("clock.geometry.x") == DEFAULT_CONFIG["clock"]["geometry"]["x"]


def test_update_clock_params_saves_to_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / ".config" / "pvfclock2.yaml"
    config = AppConfig.load(config_path)

    config.update_clock_params(
        {
            "x": 1,
            "y": 2,
            "w": 3,
            "h": 4,
            "lcd_back": "#111111",
            "lcd_face": "#222222",
            "clock_back": "#333333",
            "icon": "/tmp/icon.svg",
        }
    )

    written = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert written["clock"]["geometry"] == {"x": 1, "y": 2, "w": 3, "h": 4}
    assert written["clock"]["colors"]["lcd_face"] == "#222222"
    assert written["clock"]["icon"] == "/tmp/icon.svg"
