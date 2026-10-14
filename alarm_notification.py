from pathlib import Path
import logging

from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton

try:
    from PyQt5.QtMultimedia import QSoundEffect
except ImportError:
    QSoundEffect = None


class AlarmNotification(QDialog):
    flashing = pyqtSignal(bool)

    def __init__(self, alarm, settings, parent=None, *, text_color: str = '#7fff00'):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setWindowTitle('Alarm')
        self.setMinimumWidth(300)
        self.setStyleSheet(f'QLabel, QPushButton {{ color: {text_color}; }}')
        self.sound = None
        self.phase = False
        layout = QVBoxLayout(self)
        label = QLabel(f"{alarm.label or 'Alarm'}\n{alarm.due.astimezone():%d %b %Y %H:%M %Z}")
        label.setTextFormat(Qt.PlainText)
        layout.addWidget(label)
        self.audio_status = QLabel()
        layout.addWidget(self.audio_status)
        dismiss = QPushButton('Dismiss')
        dismiss.clicked.connect(self.accept)
        dismiss.setDefault(True)
        layout.addWidget(dismiss)
        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self.flash)
        self.flash_timer.start(500)
        sound = settings.get('sound', {})
        if not isinstance(sound, dict):
            sound = {}
        try:
            seconds = max(1, min(30, float(sound.get('duration_seconds', 30))))
        except (TypeError, ValueError):
            seconds = 30
        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.timeout.connect(self.stop_alert)
        self.stop_timer.start(int(seconds * 1000))
        if sound.get('enabled', True):
            if QSoundEffect is None:
                self.audio_status.setText('Audio unavailable; alarm shown here.')
            else:
                self.sound = QSoundEffect(self)
                self.sound.statusChanged.connect(self.audio_changed)
                self.sound.setSource(QUrl.fromLocalFile(str(Path(__file__).parent / 'assets' / 'alarm.wav')))
                self.sound.setLoopCount(QSoundEffect.Infinite)
                self.sound.setVolume(0.7)
                self.sound.play()

    def audio_changed(self):
        if self.sound.status() == QSoundEffect.Error:
            logging.getLogger(__name__).warning('Alarm audio unavailable')
            self.audio_status.setText('Audio unavailable; alarm shown here.')

    def flash(self):
        self.phase = not self.phase
        self.flashing.emit(self.phase)

    def stop_alert(self):
        self.flash_timer.stop()
        self.stop_timer.stop()
        if self.sound:
            self.sound.stop()
        self.flashing.emit(False)

    def done(self, result):
        self.stop_alert()
        super().done(result)

    def closeEvent(self, event):
        self.stop_alert()
        super().closeEvent(event)
