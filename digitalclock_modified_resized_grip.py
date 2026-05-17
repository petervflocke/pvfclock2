#!/usr/bin/env python
import sys
from mycalendar import CalendarApp
from PyQt5.QtWidgets import QSizeGrip, QApplication, QMainWindow, QLCDNumber, QLabel, QVBoxLayout, QWidget, QSizeGrip, QStatusBar, QAction
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtCore import QTime, QTimer, Qt
from datetime import date

from config import read_config, write_config


lcd_margin = 1  # Define the LCD container margin
win_margin = 1  # Define the window margin
params = { # define default parameters to ba saved in config_file_path = expanduser("~/.config/pvfclock.conf") see config.py file
        'x': 2250,
        'y': 40,
        'w': 300,
        'h': 140,
        'lcd_back': '#006400',
        'lcd_face': '#7fff00',
        'clock_back': '#2f4f4f',
        'icon' : '/usr/share/icons/hicolor/scalable/apps/org.gnome.clocks.svg'
}

class CustomStatusBar(QStatusBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent
        self.sizeGrip = QSizeGrip(self)
        self.sizeGrip.setFixedSize(50, 50)
        palette = QPalette()
        palette.setColor(QPalette.WindowText, QColor('white'))
        self.sizeGrip.setPalette(palette)
        self.addPermanentWidget(self.sizeGrip)

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
    def __init__(self):
        super().__init__()
        # Create the main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(win_margin, win_margin, win_margin, win_margin)
        
        status_bar = CustomStatusBar(self)
        status_bar.setSizeGripEnabled(True)
        self.setStatusBar(status_bar)
        #status_bar.setStyleSheet(f"color: {params['lcd_face']}; background: {params['lcd_back']};")
        #status_bar.setStyleSheet(f"color: {params['lcd_face']}; background: {params['clock_back']};")
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
        #self.setStyleSheet(f"background-color: {params['clock_back']};")
        main_window_background = f"background-color: {params['clock_back']};"
        shared_style = """
            background-color: #000000;
            color: #ffffff;
            border: 1px solid #ffffff;
        """
        # self.setStyleSheet(
        #     f"QWidget {{ {main_window_background} }} QToolTip {{ {shared_style} }} QMenu {{ {shared_style} }}"
        # )
        quitAction = QAction("E&xit", self, shortcut="Ctrl+Q",
                triggered=QApplication.instance().quit)
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

    def mouseDoubleClickEvent(self, event):
        write_config({
            'x': self.pos().x(),
            'y': self.pos().y(),
            'w': self.width(),
            'h': self.height(),
            'lcd_back': params['lcd_back'],
            'lcd_face': params['lcd_face'],
            'clock_back': params['clock_back'],
            'icon' : params['icon']
        })

    def show_calendar(self, event):
        self.calendar_app = CalendarApp()
        x, y = self.pos().x() + 0, self.pos().y() + self.size().height() + 40
        self.calendar_app.move(x, y)

    def mouseMoveEvent(self, event):
        newPos = event.globalPos() - self.offset
        self.move(newPos)

    def mousePressEvent(self, event):
        self.offset = event.pos()

    # add fake window decorator to close window?
    def close_application(self):
        self.close()

    def resizeEvent(self, event):
        self.update_lcd_geometry()

    def update_lcd_geometry(self):
        lcd_container_size = self.lcd_container.size()
        self.lcd1.setGeometry(0, 0, lcd_container_size.width(), lcd_container_size.height())
        self.lcd2.setGeometry(0, 0, lcd_container_size.width(), lcd_container_size.height())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    params = read_config(params)
    window = MainWindow()
    sys.exit(app.exec_())
