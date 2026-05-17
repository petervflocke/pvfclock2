from PyQt5.QtWidgets import QApplication, QMainWindow, QStatusBar, QSizeGrip
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create a status bar
        self.status_bar = QStatusBar(self)
        self.status_bar.showMessage("Status Bar with Size Grip")

        # Enable the size grip in the status bar
        self.status_bar.setSizeGripEnabled(True)

        # Access the existing size grip and set its color
        size_grip = self.status_bar.findChild(QSizeGrip)
        palette = QPalette()
        palette.setColor(QPalette.WindowText, QColor('#FF0000'))
        size_grip.setPalette(palette)

        # Set the status bar for the main window
        self.setStatusBar(self.status_bar)


        main_window_background = f"background-color: #FFFFFF;"
        shared_style = """
            background-color: #FFFFFF;
            color: #ffffff;
            border: 1px solid #000000;
        """
        self.setStyleSheet(
            f"QWidget {{ {main_window_background} }} QToolTip {{ {shared_style} }} QMenu {{ {shared_style} }}"
        )

        # Set the window title and size
        self.setWindowTitle("Window with Status Bar and Size Grip")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setGeometry(100, 100, 500, 300)

# Create the application and the main window
app = QApplication([])
window = MainWindow()
window.show()

# Run the application
app.exec_()
