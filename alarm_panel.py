from datetime import datetime, timedelta

from PyQt5.QtCore import QDate, Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QDateEdit, QPushButton, QInputDialog)

from app_config import AppConfig
from alarm_model import Alarm, UTC, local_zone, parse_time, resolve_local


class TimeInput(QLineEdit):
    def step(self, delta: int) -> None:
        try:
            hour, minute = parse_time(self.text())
        except ValueError:
            hour, minute = 0, 0
        hours = self.cursorPosition() < 3
        if hours:
            hour = (hour + delta) % 24
        else:
            minute = (minute + delta) % 60
        self.setText(f'{hour:02}:{minute:02}')
        self.setSelection(0 if hours else 3, 2)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            self.step(1 if event.key() == Qt.Key_Up else -1)
        elif event.key() in (Qt.Key_Left, Qt.Key_Right):
            self.setSelection(0 if event.key() == Qt.Key_Left else 3, 2)
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        if self.hasFocus():
            self.step(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
        else:
            event.ignore()


class AlarmPanel(QWidget):
    armed = pyqtSignal(object)
    cancelled = pyqtSignal()
    hidden = pyqtSignal()

    def __init__(self, config: AppConfig):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle('One-time alarm')
        self.zone = local_zone()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('One-time alarm'))
        row = QHBoxLayout()
        self.time = TimeInput()
        self.time.setAccessibleName('Alarm time HH:MM')
        self.time.setText((datetime.now(self.zone) + timedelta(minutes=5)).strftime('%H:%M'))
        row.addWidget(self.time)
        for label, delta in [('▲', 1), ('▼', -1)]:
            button = QPushButton(label)
            button.setFixedWidth(30)
            button.setFocusPolicy(Qt.NoFocus)
            button.clicked.connect(lambda checked, step=delta: self.time.step(step))
            row.addWidget(button)
        layout.addLayout(row)
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat('yyyy-MM-dd')
        self.date.setAccessibleName('Alarm date')
        layout.addWidget(self.date)
        self.label = QLineEdit()
        self.label.setPlaceholderText('Optional label')
        layout.addWidget(self.label)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        layout.addWidget(self.preview)
        self.status = QLabel('No alarm')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        self.cancel_button = QPushButton('Cancel alarm')
        self.cancel_button.setEnabled(False)
        self.set_button = QPushButton('Set alarm')
        row.addWidget(self.cancel_button)
        row.addWidget(self.set_button)
        layout.addLayout(row)
        self.set_button.clicked.connect(self.confirm)
        self.cancel_button.clicked.connect(self.cancelled)
        self.time.textChanged.connect(self.update_preview)
        self.date.dateChanged.connect(self.update_preview)
        self.configure(config)
        self.update_preview()
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(lambda: self.update_preview() if self.isVisible() else None)
        self.preview_timer.start(1000)

    def configure(self, config: AppConfig) -> None:
        self.set_button.setEnabled(not config.temporary)
        self.setStyleSheet(
            f"QWidget {{ background: {config.get('clock.colors.panel_back')}; "
            f"color: {config.get('clock.colors.panel_text')}; }} "
            f"QPushButton:disabled {{ color: {config.get('clock.colors.panel_muted')}; }}"
        )
        if config.temporary:
            self.status.setText('Temporary defaults: fix YAML and reload to arm.')

    def candidates(self) -> list[datetime]:
        hour, minute = parse_time(self.time.text())
        day = self.date.date().toPyDate()
        now = datetime.now(self.zone)
        naive = datetime(day.year, day.month, day.day, hour, minute)
        choices = resolve_local(naive, self.zone)
        if not choices:
            raise ValueError('That local time does not exist (daylight-saving change).')
        if day == now.date() and all(value <= now for value in choices):
            naive += timedelta(days=1)
            choices = resolve_local(naive, self.zone)
        choices = [value for value in choices if value > now]
        if not choices:
            raise ValueError('Choose a future date and time.')
        return choices

    def update_preview(self) -> None:
        try:
            choices = self.candidates()
            when = choices[0].astimezone(self.zone)
            minutes = max(0, int((choices[0] - datetime.now(UTC)).total_seconds() / 60))
            self.preview.setText(f"{when:%a %d %b %Y, %H:%M %Z} — in {minutes} min" +
                                 (' (two occurrences; select when setting)' if len(choices) > 1 else ''))
        except ValueError as error:
            self.preview.setText(str(error))

    def confirm(self) -> None:
        if not self.set_button.isEnabled():
            return
        try:
            choices = self.candidates()
            selected = choices[0]
            if len(choices) > 1:
                labels = [value.astimezone(self.zone).strftime('%H:%M %Z (UTC%z)') for value in choices]
                choice, accepted = QInputDialog.getItem(self, 'Repeated local time', 'Choose occurrence:', labels, 0, False)
                if not accepted:
                    return
                selected = choices[labels.index(choice)]
            self.armed.emit(Alarm.create(selected, self.zone.key, self.label.text(), datetime.now(UTC)))
        except ValueError as error:
            self.status.setText(str(error))

    def show_alarm(self, alarm: Alarm | None) -> None:
        self.cancel_button.setEnabled(bool(alarm and alarm.state == 'armed'))
        self.status.setText('No alarm' if alarm is None else
                            f"{alarm.state.title()}: {alarm.due.astimezone(self.zone):%d %b %H:%M} {alarm.label}")

    def open_editor(self, alarm: Alarm | None) -> None:
        if alarm and alarm.state == 'armed':
            when = alarm.due.astimezone(self.zone)
            self.time.setText(when.strftime('%H:%M'))
            self.date.setDate(QDate(when.year, when.month, when.day))
            self.label.setText(alarm.label)
        else:
            self.time.setText((datetime.now(self.zone) + timedelta(minutes=5)).strftime('%H:%M'))
            self.date.setDate(QDate.currentDate())
            self.label.clear()
        self.show()
        self.activateWindow()
        self.time.setFocus()
        self.time.selectAll()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.hidden.emit()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.confirm()
        else:
            super().keyPressEvent(event)
