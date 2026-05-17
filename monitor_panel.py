from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from metrics_provider import MetricValue
from sparkline_widget import SparklineWidget


class MonitorPanel(QWidget):
    def __init__(self, app_config: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self.app_config = app_config
        self.setWindowTitle("DCLOCK Monitor")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.apply_config(app_config)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        self.content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(5)
        self.content.setLayout(self.content_layout)

        self.rows: dict[str, MetricRow] = {}
        self.has_stretch = False
        for row_key, label, value, graph_enabled in self._placeholder_rows():
            self._ensure_row(row_key, label, graph_enabled).set_value(value)
        self._ensure_stretch()

        scroll_area.setWidget(self.content)
        layout.addWidget(scroll_area)
        self.setLayout(layout)
        self.resize(300, self._panel_height())

    def apply_config(self, app_config: Any) -> None:
        self.app_config = app_config
        colors = self._colors()
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {colors["panel_back"]};
                color: {colors["panel_text"]};
            }}
            QLabel#metricValue {{
                color: {colors["panel_text"]};
                font-weight: bold;
            }}
            QLabel#metricLabel {{
                color: {colors["panel_muted"]};
            }}
            QLabel#metricRange {{
                color: {colors["panel_muted"]};
                font-size: 10px;
            }}
            QLabel#metricAxis {{
                color: {colors["panel_muted"]};
                font-size: 9px;
            }}
            QLabel#metricLabelLarge {{
                color: {colors["panel_muted"]};
                font-size: 14px;
            }}
            QLabel#metricValueLarge {{
                color: {colors["panel_text"]};
                font-size: 16px;
                font-weight: bold;
            }}
            QScrollArea {{
                border: 0;
            }}
            """
        )
        if hasattr(self, "rows"):
            graph_line_color = str(self.app_config.get("clock.colors.graph_line", "#7fff00"))
            graph_grid_color = str(self.app_config.get("clock.colors.graph_grid", "#5f6b6b"))
            for row in self.rows.values():
                row.set_graph_colors(graph_line_color, graph_grid_color)
            self.resize(self.width(), self._panel_height())

    def set_metrics(self, metrics: list[MetricValue], history: dict[str, list[float]]) -> None:
        seen: set[str] = set()
        for metric in metrics:
            for row_key, graph_enabled in self._display_rows_for_metric(metric):
                seen.add(row_key)
                row = self._ensure_row(row_key, metric.label, graph_enabled)
                row.set_label(metric.label)
                row.set_value(metric.display_value)
                row.set_alarm_state(metric.value, self._alarm_config_for_metric(metric))
                row.set_history(history.get(metric.key, []))

        for key, row in self.rows.items():
            if key.startswith("placeholder."):
                row.setVisible(not metrics)
            elif key not in seen:
                row.hide()
        self.updateGeometry()
        self.resize(self.width(), self._panel_height())

    def dock_to_clock(self, clock_window: QWidget) -> None:
        width = self._panel_width(clock_window)
        height = self._panel_height()
        self.resize(width, height)
        self.move(clock_window.x(), clock_window.y() + clock_window.height())

    def _ensure_row(self, key: str, label: str, graph_enabled: bool) -> "MetricRow":
        if key in self.rows:
            row = self.rows[key]
            row.set_graph_enabled(graph_enabled)
            row.show()
            return row

        row = MetricRow(
            label=label,
            graph_enabled=graph_enabled,
            graph_line_color=str(self.app_config.get("clock.colors.graph_line", "#7fff00")),
            graph_grid_color=str(self.app_config.get("clock.colors.graph_grid", "#5f6b6b")),
        )
        if self.has_stretch:
            self.content_layout.insertWidget(max(0, self.content_layout.count() - 1), row)
        else:
            self.content_layout.addWidget(row)
        self.rows[key] = row
        self._ensure_stretch()
        return row

    def _placeholder_rows(self) -> list[tuple[str, str, str, bool]]:
        rows: list[tuple[str, str, str, bool]] = []
        for key, label in (
            ("system_load", str(self.app_config.get("metrics.system_load.label", "System Load"))),
            ("cpu", str(self.app_config.get("metrics.cpu.label", "CPU"))),
            ("memory", str(self.app_config.get("metrics.memory.label", "Memory"))),
        ):
            for suffix, graph_enabled in self._display_rows_for_key(key):
                rows.append((f"placeholder.{key}.{suffix}", label, "n/a", graph_enabled))
        return rows

    def _ensure_stretch(self) -> None:
        if not self.has_stretch:
            self.content_layout.addStretch(1)
            self.has_stretch = True

    def _graph_enabled_for_key(self, key: str) -> bool:
        if key == "system_load":
            return bool(self.app_config.get("metrics.system_load.graph.enabled", True))
        if key == "cpu":
            return bool(self.app_config.get("metrics.cpu.graph.enabled", True))
        if key == "memory":
            return bool(self.app_config.get("metrics.memory.graph.enabled", True))
        return False

    def _text_enabled_for_key(self, key: str) -> bool:
        if key == "system_load":
            return bool(self.app_config.get("metrics.system_load.text.enabled", False))
        if key == "cpu":
            return bool(self.app_config.get("metrics.cpu.text.enabled", False))
        if key == "memory":
            return bool(self.app_config.get("metrics.memory.text.enabled", False))
        return False

    def _display_rows_for_key(self, key: str) -> list[tuple[str, bool]]:
        rows: list[tuple[str, bool]] = []
        if self._graph_enabled_for_key(key):
            rows.append(("graph", True))
        if self._text_enabled_for_key(key):
            rows.append(("text", False))
        return rows

    def _display_rows_for_metric(self, metric: MetricValue) -> list[tuple[str, bool]]:
        rows: list[tuple[str, bool]] = []
        if self._graph_enabled_for_metric(metric):
            rows.append((f"{metric.key}.graph", True))
        if self._text_enabled_for_metric(metric):
            rows.append((f"{metric.key}.text", False))
        return rows

    def _graph_enabled_for_metric(self, metric: MetricValue) -> bool:
        key = metric.key
        if not key.startswith("temperature."):
            if key.startswith("network."):
                feature_config = self._network_feature_config(key)
                if feature_config is not None:
                    graph_config = feature_config.get("graph", {})
                    if isinstance(graph_config, dict) and "enabled" in graph_config:
                        return bool(graph_config["enabled"])
            return self._graph_enabled_for_key(key)

        feature_config = self._temperature_feature_config(key)
        if feature_config is not None:
            graph_config = feature_config.get("graph", {})
            if isinstance(graph_config, dict) and "enabled" in graph_config:
                return bool(graph_config["enabled"])
        return bool(self.app_config.get("metrics.temperatures.graph.enabled", True))

    def _text_enabled_for_metric(self, metric: MetricValue) -> bool:
        key = metric.key
        if not key.startswith("temperature."):
            if key.startswith("network."):
                feature_config = self._network_feature_config(key)
                if feature_config is not None:
                    text_config = feature_config.get("text", {})
                    if isinstance(text_config, dict) and "enabled" in text_config:
                        return bool(text_config["enabled"])
            return self._text_enabled_for_key(key)

        feature_config = self._temperature_feature_config(key)
        if feature_config is not None:
            text_config = feature_config.get("text", {})
            if isinstance(text_config, dict) and "enabled" in text_config:
                return bool(text_config["enabled"])
        return False

    def _temperature_feature_config(self, key: str) -> dict[str, Any] | None:
        parts = key.split(".", 2)
        if len(parts) != 3:
            return None

        chip_name, feature_name = parts[1], parts[2]
        chips = self.app_config.get("metrics.temperatures.chips", {})
        if not isinstance(chips, dict):
            return None
        chip_config = chips.get(chip_name, {})
        if not isinstance(chip_config, dict):
            return None
        features = chip_config.get("features", {})
        if not isinstance(features, dict):
            return None
        feature_config = features.get(feature_name, {})
        if not isinstance(feature_config, dict):
            return None
        return feature_config

    def _network_feature_config(self, key: str) -> dict[str, Any] | None:
        parts = key.split(".", 2)
        if len(parts) != 3:
            return None

        interface_name, feature_name = parts[1], parts[2]
        interfaces = self.app_config.get("metrics.network.interfaces", {})
        if not isinstance(interfaces, dict):
            return None
        interface_config = interfaces.get(interface_name, {})
        if not isinstance(interface_config, dict):
            return None
        features = interface_config.get("features", {})
        if not isinstance(features, dict):
            return None
        feature_config = features.get(feature_name, {})
        if not isinstance(feature_config, dict):
            return None
        return feature_config

    def _alarm_config_for_metric(self, metric: MetricValue) -> dict[str, object]:
        key = metric.key
        if key == "system_load":
            return self._alarm_config("metrics.system_load.alarm")
        if key == "cpu":
            return self._alarm_config("metrics.cpu.alarm")
        if key == "memory":
            return self._alarm_config("metrics.memory.alarm")
        if key.startswith("network."):
            feature_config = self._network_feature_config(key)
            if feature_config is None:
                return {}
            alarm_config = feature_config.get("alarm", {})
            if isinstance(alarm_config, dict):
                return alarm_config
            return {}
        if not key.startswith("temperature."):
            return {}

        parts = key.split(".", 2)
        if len(parts) != 3:
            return {}
        chip_name, feature_name = parts[1], parts[2]
        chips = self.app_config.get("metrics.temperatures.chips", {})
        if not isinstance(chips, dict):
            return {}
        chip_config = chips.get(chip_name, {})
        if not isinstance(chip_config, dict):
            return {}
        features = chip_config.get("features", {})
        if not isinstance(features, dict):
            return {}
        feature_config = features.get(feature_name, {})
        if not isinstance(feature_config, dict):
            return {}
        alarm_config = feature_config.get("alarm", {})
        if isinstance(alarm_config, dict):
            return alarm_config
        return {}

    def _alarm_config(self, dotted_key: str) -> dict[str, object]:
        alarm_config = self.app_config.get(dotted_key, {})
        if isinstance(alarm_config, dict):
            return alarm_config
        return {}

    def _panel_width(self, clock_window: QWidget) -> int:
        width_mode = self.app_config.get("monitor_panel.width_mode", "clock")
        if width_mode == "fixed":
            return int(self.app_config.get("monitor_panel.fixed_width", clock_window.width()))
        return clock_window.width()

    def _panel_height(self) -> int:
        min_height = int(self.app_config.get("monitor_panel.min_height", 120))
        max_height = int(self.app_config.get("monitor_panel.max_height", 600))
        if str(self.app_config.get("monitor_panel.height_mode", "fixed")) == "auto" and hasattr(self, "rows"):
            height = self._content_height()
            return max(min_height, min(max_height, height))
        height = int(self.app_config.get("monitor_panel.height", 260))
        return max(min_height, min(max_height, height))

    def _content_height(self) -> int:
        layout = self.layout()
        layout_top = layout_bottom = 0
        if layout is not None:
            margins = layout.contentsMargins()
            layout_top = margins.top()
            layout_bottom = margins.bottom()

        content_margins = self.content_layout.contentsMargins()
        height = layout_top + layout_bottom + content_margins.top() + content_margins.bottom()
        spacing = self.content_layout.spacing()
        visible_rows = [row for row in self.rows.values() if row.isVisible()]
        for index, row in enumerate(visible_rows):
            row_height = max(row.sizeHint().height(), row.minimumHeight())
            height += row_height
            if index:
                height += spacing
        return height + 4

    def _colors(self) -> dict[str, str]:
        return {
            "panel_back": str(self.app_config.get("clock.colors.panel_back", "#1f2929")),
            "panel_text": str(self.app_config.get("clock.colors.panel_text", "#d8ffd0")),
            "panel_muted": str(self.app_config.get("clock.colors.panel_muted", "#7fa37f")),
        }


class MetricRow(QWidget):
    def __init__(
        self,
        label: str,
        graph_enabled: bool,
        graph_line_color: str,
        graph_grid_color: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 1, 0, 4)
        layout.setSpacing(2)

        self.header_widget = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        self.label_widget = QLabel(label)
        self.label_widget.setObjectName("metricLabel")
        self.value_widget = QLabel("n/a")
        self.value_widget.setObjectName("metricValue")
        self.value_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        row_layout.addWidget(self.label_widget, 1)
        row_layout.addStretch(1)
        row_layout.addWidget(self.value_widget)
        self.header_widget.setLayout(row_layout)
        layout.addWidget(self.header_widget)

        self.graph_widget = QWidget()
        graph_layout = QHBoxLayout()
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(6)

        axis_layout = QVBoxLayout()
        axis_layout.setContentsMargins(0, 0, 0, 0)
        axis_layout.setSpacing(0)
        self.max_widget = QLabel("")
        self.max_widget.setObjectName("metricAxis")
        self.max_widget.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.min_widget = QLabel("")
        self.min_widget.setObjectName("metricAxis")
        self.min_widget.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        axis_layout.addWidget(self.max_widget)
        axis_layout.addStretch(1)
        axis_layout.addWidget(self.min_widget)

        self.sparkline = SparklineWidget(graph_line_color, graph_grid_color)
        graph_layout.addLayout(axis_layout)
        graph_layout.addWidget(self.sparkline, 1)
        self.graph_widget.setLayout(graph_layout)
        layout.addWidget(self.graph_widget)

        self.setLayout(layout)
        self.normal_line_color = graph_line_color
        self.graph_enabled = graph_enabled
        self.set_graph_enabled(graph_enabled)

    def set_label(self, label: str) -> None:
        self.label_widget.setText(label)

    def set_value(self, value: str) -> None:
        self.value_widget.setText(value)

    def set_history(self, values: list[float]) -> None:
        self.sparkline.set_values(values)
        minimum, maximum = self._format_axis_values(values)
        self.min_widget.setText(minimum)
        self.max_widget.setText(maximum)

    def set_graph_colors(self, line_color: str, grid_color: str) -> None:
        self.normal_line_color = line_color
        self.sparkline.set_line_color(line_color)
        self.sparkline.set_grid_color(grid_color)

    def set_alarm_state(self, value: float | None, alarm_config: dict[str, object]) -> None:
        alarm_max = alarm_config.get("max")
        alarm_color = str(alarm_config.get("color", "#ff5555"))
        if value is None or alarm_max is None:
            self.sparkline.set_line_color(self.normal_line_color)
            self.sparkline.set_alarm_threshold(None)
            self.value_widget.setStyleSheet("")
            return
        try:
            threshold = float(alarm_max)
        except (TypeError, ValueError):
            self.sparkline.set_line_color(self.normal_line_color)
            self.sparkline.set_alarm_threshold(None)
            self.value_widget.setStyleSheet("")
            return

        is_alarm = value >= threshold
        self.sparkline.set_line_color(self.normal_line_color)
        self.sparkline.set_alarm_threshold(threshold, alarm_color)
        self.value_widget.setStyleSheet(f"color: {alarm_color};" if is_alarm and not self.graph_enabled else "")

    def set_graph_enabled(self, enabled: bool) -> None:
        self.graph_enabled = enabled
        self.graph_widget.setVisible(enabled)
        self.setMinimumHeight(58)
        self.label_widget.setObjectName("metricLabel" if enabled else "metricLabelLarge")
        self.value_widget.setObjectName("metricValue" if enabled else "metricValueLarge")
        self.style().unpolish(self.label_widget)
        self.style().polish(self.label_widget)
        self.style().unpolish(self.value_widget)
        self.style().polish(self.value_widget)

    def _format_axis_values(self, values: list[float]) -> tuple[str, str]:
        if not values:
            return "", ""

        minimum = min(values)
        maximum = max(values)
        current_text = self.value_widget.text().strip()
        unit = ""
        if current_text.endswith("%"):
            unit = "%"
        elif current_text.endswith(" C"):
            unit = " C"
        elif current_text.endswith("/s"):
            unit = "/s"

        if unit == "%":
            return f"{minimum:.0f}%", f"{maximum:.0f}%"
        if unit == " C":
            return f"{minimum:.1f}", f"{maximum:.1f}"
        if unit == "/s":
            return _format_rate(minimum), _format_rate(maximum)
        return f"{minimum:.2f}", f"{maximum:.2f}"


def _format_rate(value: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = value
    for unit in units:
        if abs(size) < 1024.0 or unit == units[-1]:
            return f"{size:.1f}{unit}/s"
        size /= 1024.0
    return f"{size:.1f}TiB/s"
