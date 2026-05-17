import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, QPushButton
from PyQt5.QtCore import QDate

class CalendarApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Create a QVBoxLayout to organize widgets
        vbox = QVBoxLayout()

        # Create a QHBoxLayout to organize the calendars horizontally
        hbox_calendars = QHBoxLayout()

        # Create three QCalendarWidgets and add them to the layout
        self.calendar1 = QCalendarWidget()
        self.calendar2 = QCalendarWidget()
        self.calendar3 = QCalendarWidget()

        # Remove highlighting of the current date
        self.calendar1.setStyleSheet("QCalendarWidget QWidget { alternate-background-color: white; }")
        self.calendar2.setStyleSheet("QCalendarWidget QWidget { alternate-background-color: white; }")
        self.calendar3.setStyleSheet("QCalendarWidget QWidget { alternate-background-color: white; }")

        # Set the months
        self.reset_calendars()

        hbox_calendars.addWidget(self.calendar1)
        hbox_calendars.addWidget(self.calendar2)
        hbox_calendars.addWidget(self.calendar3)

        vbox.addLayout(hbox_calendars)

        # Create a QHBoxLayout to organize the buttons horizontally
        hbox_buttons = QHBoxLayout()

        # Create buttons to move months
        self.button_prev = QPushButton('Previous Month')
        self.button_prev.clicked.connect(self.move_previous_month)
        self.button_reset = QPushButton('Reset to Current Month')
        self.button_reset.clicked.connect(self.reset_calendars)
        self.button_next = QPushButton('Next Month')
        self.button_next.clicked.connect(self.move_next_month)

        hbox_buttons.addWidget(self.button_prev)
        hbox_buttons.addWidget(self.button_reset)
        hbox_buttons.addWidget(self.button_next)

        vbox.addLayout(hbox_buttons)

        # Set the layout for the window
        self.setLayout(vbox)

        # Set window properties
        self.setWindowTitle('Three Months Calendar')
        self.setGeometry(100, 100, 900, 200)
        self.show()

    def reset_calendars(self):
        date = QDate.currentDate()
        self.calendar1.setSelectedDate(date.addMonths(-1))
        self.calendar2.setSelectedDate(date)
        self.calendar3.setSelectedDate(date.addMonths(1))

    def move_previous_month(self):
        self.calendar1.setSelectedDate(self.calendar1.selectedDate().addMonths(-1))
        self.calendar2.setSelectedDate(self.calendar2.selectedDate().addMonths(-1))
        self.calendar3.setSelectedDate(self.calendar3.selectedDate().addMonths(-1))

    def move_next_month(self):
        self.calendar1.setSelectedDate(self.calendar1.selectedDate().addMonths(1))
        self.calendar2.setSelectedDate(self.calendar2.selectedDate().addMonths(1))
        self.calendar3.setSelectedDate(self.calendar3.selectedDate().addMonths(1))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CalendarApp()
    sys.exit(app.exec_())
