#!/usr/bin/env python
import sys
from mycalendar import CalendarApp
from PyQt5.QtWidgets import QApplication, QMainWindow, QLCDNumber, QLabel, QVBoxLayout, QWidget, QSizeGrip, QStatusBar, QAction
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtCore import QTime, QTimer, Qt
from datetime import date

from app_config import AppConfig, DEFAULT_CONFIG
from monitor_controller import MonitorController
from monitor_panel import MonitorPanel


lcd_margin = 1  # Define the LCD container margin
win_margin = 1  # Define the window margin
params = {
        'x': DEFAULT_CONFIG["clock"]["geometry"]["x"],
        'y': DEFAULT_CONFIG["clock"]["geometry"]["y"],
        'w': DEFAULT_CONFIG["clock"]["geometry"]["w"],
        'h': DEFAULT_CONFIG["clock"]["geometry"]["h"],
        'lcd_back': DEFAULT_CONFIG["clock"]["colors"]["lcd_back"],
        'lcd_face': DEFAULT_CONFIG["clock"]["colors"]["lcd_face"],
        'clock_back': DEFAULT_CONFIG["clock"]["colors"]["clock_back"],
        'icon' : DEFAULT_CONFIG["clock"]["icon"]
}

class CustomStatusBar(QStatusBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent

    def mouseDoubleClickEvent(self, event):
        self.main_window.show_calendar()

class DigitalClock(QLCDNumber):
    def __init__(self, parent=None, status_bar=None):
        super(DigitalClock, self).__init__(parent)
        self.status_bar = status_bar
        timer = QTimer(self)
        timer.timeout.connect(self.showTime)
        timer.start(1000)
        self.showTime()

    def showTime(self):
        time = QTime.currentTime()
        text = time.toString('hh:mm')
        if (time.second() % 2) == 0:
            text = text[:2] + ' ' + text[3:]
        self.display(text)
        if self.status_bar:
            self.status_bar.showMessage(date.today().strftime("%d.%m.%y, %A, %B, W%U"))

        text = time.toString('hh:mm')
        if (time.second() % 2) == 0:
            text = text[:2] + ' ' + text[3:]
        self.display(text)

class MainWindow(QMainWindow):
    def __init__(self, app_config):
        super().__init__()
        self.app_config = app_config
        self.monitor_panel = MonitorPanel(app_config)
        self.monitor_controller = MonitorController(app_config, self.monitor_panel)
        self._shutdown_started = False
        self._shutdown_complete = False
        self.monitor_controller.shutdown_finished.connect(self.finish_shutdown)
        # Create the main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(win_margin, win_margin, win_margin, win_margin)
        
        status_bar = CustomStatusBar(self)
        self.setStatusBar(status_bar)
        status_bar.setStyleSheet(f"color: {params['lcd_face']}; background: {params['lcd_back']};")
        status_bar.setStyleSheet(f"color: {params['lcd_face']}; background: {params['clock_back']};")
        status_bar.mouseDoubleClickEvent = self.show_calendar

        # Container for lcd1 and lcd2 (overlaying each other)
        self.lcd_container = QWidget()
        self.lcd_container.setLayout(QVBoxLayout())
        self.lcd_container.layout().setContentsMargins(lcd_margin, lcd_margin, lcd_margin, lcd_margin)  # Set the LCD container margins

        self.lcd1 = QLCDNumber(self.lcd_container)
        self.lcd1.setDigitCount(5)
        self.lcd1.setSegmentStyle(QLCDNumber.Flat)
        self.lcd1.display("88:88")
        palette1 = self.lcd1.palette()
        palette1.setColor(palette1.WindowText, QColor(params['lcd_back']))
        self.lcd1.setPalette(palette1)
        self.lcd1.setFrameStyle(0)

        self.lcd2 = DigitalClock(self.lcd_container, status_bar=status_bar)
        self.lcd2.setSegmentStyle(QLCDNumber.Flat)
        self.lcd2.setDigitCount(5)
        palette2 = self.lcd2.palette()
        palette2.setColor(palette2.WindowText, QColor(params['lcd_face']))
        self.lcd2.setPalette(palette2)
        self.lcd2.setFrameStyle(0)
        self.lcd2.setWindowFlags(Qt.FramelessWindowHint)
        self.lcd2.setAttribute(Qt.WA_TranslucentBackground)

        # Add the LCD container to the main layout
        main_layout.addWidget(self.lcd_container)

        # # Create the label
        # self.label = QLabel("Hello world")
        # self.label.setStyleSheet("color: #7fff00")

        # # Add the label to the main layout
        # main_layout.addWidget(self.label)

        # Create a central widget and set the main layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        main_layout.setSpacing(0)

        self.resize(params['w'], params['h'])
        self.move(params['x'], params['y'])
        self.setWindowTitle("DCLOCK")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.apply_clock_style()
        self.toggleMonitorAction = QAction(
                "Toggle Monitor", self,
                shortcut=str(self.app_config.get("monitor_panel.shortcut", "Ctrl+1")),
                triggered=self.toggle_monitor)
        self.toggleMonitorAction.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(self.toggleMonitorAction)
        self.reloadConfigAction = QAction(
                "Reload Config", self,
                shortcut=str(self.app_config.get("app.reload_shortcut", "Ctrl+R")),
                triggered=self.reload_config)
        self.reloadConfigAction.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(self.reloadConfigAction)
        quitAction = QAction("E&xit", self, shortcut="Ctrl+Q",
                triggered=self.close)
        quitAction.setShortcutContext(Qt.ApplicationShortcut)
        self.addAction(quitAction)
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.setToolTip("Drag the clock with the left mouse button.\n"
                "Use the right mouse button to open a context menu.\n"
                "Double click time to save current position on screen.\n"
                "Double click date to open calendar")
    
        try:
            icon = QIcon(params['icon'])
        except Exception as e:
            print(f"Error loading icon: {e}")
            icon = QIcon.standardIcon(Qt.Application)
        self.setWindowIcon(icon)

        self.show()
        self.update_lcd_geometry()
        self.dock_monitor_panel()
        self.monitor_controller.start()

    def mouseDoubleClickEvent(self, event):
        self.app_config.update_clock_params({
            'x': self.pos().x(),
            'y': self.pos().y(),
            'w': self.width(),
            'h': self.height(),
            'lcd_back': params['lcd_back'],
            'lcd_face': params['lcd_face'],
            'clock_back': params['clock_back'],
            'icon' : params['icon']
        })

    def show_calendar(self, event=None):
        self.calendar_app = CalendarApp()
        anchor = self.monitor_panel if self.monitor_panel.isVisible() else self
        x, y = self.pos().x(), anchor.pos().y() + anchor.size().height() + 40
        self.calendar_app.move(x, y)

    def toggle_monitor(self):
        if self.monitor_panel.isVisible():
            self.monitor_panel.hide()
            return
        self.dock_monitor_panel()
        self.monitor_panel.show()
        self.monitor_controller.poll()

    def reload_config(self):
        global params
        was_panel_visible = self.monitor_panel.isVisible()
        try:
            self.app_config = AppConfig.load(self.app_config.path)
        except Exception as error:
            print(f"Error reloading config: {error}")
            self.statusBar().showMessage(f"Config reload failed: {error}", 5000)
            return
        params = self.app_config.clock_params()
        self.toggleMonitorAction.setShortcut(str(self.app_config.get("monitor_panel.shortcut", "Ctrl+1")))
        self.reloadConfigAction.setShortcut(str(self.app_config.get("app.reload_shortcut", "Ctrl+R")))
        self.apply_clock_style()
        self.monitor_panel.apply_config(self.app_config)
        self.monitor_controller.configure(self.app_config)
        self.dock_monitor_panel()
        if was_panel_visible:
            self.monitor_panel.show()
            self.monitor_controller.refresh_external_ip()
            self.dock_monitor_panel()
        self.statusBar().showMessage("Config reloaded", 3000)

    def dock_monitor_panel(self):
        self.monitor_panel.dock_to_clock(self)

    def mouseMoveEvent(self, event):
        newPos = event.globalPos() - self.offset
        self.move(newPos)
        self.dock_monitor_panel()

    def mousePressEvent(self, event):
        self.offset = event.pos()

    # add fake window decorator to close window?
    def close_application(self):
        self.close()

    def closeEvent(self, event):
        if self._shutdown_complete:
            super().closeEvent(event)
            return
        event.ignore()
        if not self._shutdown_started:
            self._shutdown_started = True
            self.setEnabled(False)
            self.monitor_panel.hide()
            self.monitor_controller.stop()

    def finish_shutdown(self):
        self._shutdown_complete = True
        self.monitor_panel.close()
        self.close()
        QApplication.instance().quit()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "monitor_panel") and self.monitor_panel.isVisible():
            self.dock_monitor_panel()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_lcd_geometry()
        if hasattr(self, "monitor_panel") and self.monitor_panel.isVisible():
            self.dock_monitor_panel()

    def update_lcd_geometry(self):
        lcd_container_size = self.lcd_container.size()
        self.lcd1.setGeometry(0, 0, lcd_container_size.width(), lcd_container_size.height())
        self.lcd2.setGeometry(0, 0, lcd_container_size.width(), lcd_container_size.height())

    def apply_clock_style(self):
        self.statusBar().setStyleSheet(f"color: {params['lcd_face']}; background: {params['clock_back']};")
        palette1 = self.lcd1.palette()
        palette1.setColor(palette1.WindowText, QColor(params['lcd_back']))
        self.lcd1.setPalette(palette1)
        palette2 = self.lcd2.palette()
        palette2.setColor(palette2.WindowText, QColor(params['lcd_face']))
        self.lcd2.setPalette(palette2)
        main_window_background = f"background-color: {params['clock_back']};"
        shared_style = """
            background-color: #000000;
            color: #ffffff;
            border: 1px solid #ffffff;
        """
        self.setStyleSheet(
            f"QWidget {{ {main_window_background} }} QToolTip {{ {shared_style} }} QMenu {{ {shared_style} }}"
        )
        try:
            self.setWindowIcon(QIcon(params['icon']))
        except Exception as e:
            print(f"Error loading icon: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app_config = AppConfig.load()
    params = app_config.clock_params()
    window = MainWindow(app_config)
    sys.exit(app.exec_())
