from __future__ import annotations

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QWidget


class SparklineWidget(QWidget):
    def __init__(
        self,
        line_color: str = "#7fff00",
        grid_color: str = "#5f6b6b",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.values: list[float] = []
        self.line_color = line_color
        self.current_line_color = line_color
        self.alarm_threshold: float | None = None
        self.alarm_color = "#ff5555"
        self.grid_color = grid_color
        self.setFixedHeight(32)

    def set_values(self, values: list[float]) -> None:
        self.values = values
        self.update()

    def set_line_color(self, color: str) -> None:
        self.current_line_color = color
        self.update()

    def set_grid_color(self, color: str) -> None:
        self.grid_color = color
        self.update()

    def set_alarm_threshold(self, threshold: float | None, color: str = "#ff5555") -> None:
        self.alarm_threshold = threshold
        self.alarm_color = color
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = max(1, self.width() - 2)
        height = max(1, self.height() - 2)
        self._draw_grid(painter, width, height)

        minimum = min(self.values)
        maximum = max(self.values)
        span = maximum - minimum

        if len(self.values) == 1:
            color = self._color_for_value(self.values[0])
            painter.setPen(QPen(QColor(color), 1.5))
            y = 1 + height / 2
            painter.drawLine(QPointF(1, y), QPointF(width, y))
            return

        points: list[QPointF] = []
        for index, value in enumerate(self.values):
            x = 1 + (index / (len(self.values) - 1)) * width
            if span == 0:
                y = 1 + height / 2
            else:
                y = 1 + height - ((value - minimum) / span) * height
            points.append(QPointF(x, y))

        for index in range(1, len(points)):
            self._draw_segment(
                painter,
                points[index - 1],
                points[index],
                self.values[index - 1],
                self.values[index],
            )

    def _draw_grid(self, painter: QPainter, width: int, height: int) -> None:
        color = QColor(self.grid_color)
        color.setAlpha(95)
        painter.setPen(QPen(color, 0.7, Qt.DotLine))

        painter.drawLine(QPointF(1, 1), QPointF(width, 1))
        painter.drawLine(QPointF(1, height), QPointF(width, height))

        for fraction in (0.25, 0.5, 0.75):
            y = 1 + height * fraction
            painter.drawLine(QPointF(1, y), QPointF(width, y))

        for fraction in (0.25, 0.5, 0.75):
            x = 1 + width * fraction
            painter.drawLine(QPointF(x, 1), QPointF(x, height))

    def _draw_segment(
        self,
        painter: QPainter,
        start_point: QPointF,
        end_point: QPointF,
        start_value: float,
        end_value: float,
    ) -> None:
        threshold = self.alarm_threshold
        if threshold is None:
            self._draw_colored_line(painter, start_point, end_point, self.current_line_color)
            return

        start_alarm = start_value >= threshold
        end_alarm = end_value >= threshold
        if start_alarm == end_alarm:
            color = self.alarm_color if start_alarm else self.current_line_color
            self._draw_colored_line(painter, start_point, end_point, color)
            return

        value_span = end_value - start_value
        if value_span == 0:
            color = self.alarm_color if start_alarm else self.current_line_color
            self._draw_colored_line(painter, start_point, end_point, color)
            return

        fraction = (threshold - start_value) / value_span
        fraction = max(0.0, min(1.0, fraction))
        crossing_point = QPointF(
            start_point.x() + (end_point.x() - start_point.x()) * fraction,
            start_point.y() + (end_point.y() - start_point.y()) * fraction,
        )
        self._draw_colored_line(
            painter,
            start_point,
            crossing_point,
            self.alarm_color if start_alarm else self.current_line_color,
        )
        self._draw_colored_line(
            painter,
            crossing_point,
            end_point,
            self.alarm_color if end_alarm else self.current_line_color,
        )

    def _draw_colored_line(self, painter: QPainter, start_point: QPointF, end_point: QPointF, color: str) -> None:
        painter.setPen(QPen(QColor(color), 1.5))
        painter.drawLine(start_point, end_point)

    def _color_for_value(self, value: float) -> str:
        if self.alarm_threshold is not None and value >= self.alarm_threshold:
            return self.alarm_color
        return self.current_line_color
