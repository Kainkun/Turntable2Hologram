import sys
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow

class HelloWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Hello Window')
        label = QLabel('Hello', self)
        label.move(50, 50)
        self.setGeometry(100, 100, 200, 150)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = HelloWindow()
    window.show()
    sys.exit(app.exec_())
