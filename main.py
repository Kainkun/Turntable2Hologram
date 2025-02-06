# import sys
# import qdarkstyle
# from PyQt6 import uic
# from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog


# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         uic.loadUi("main_window.ui", self)  # Load the .ui file

#         # Connect the button to the function
#         self.openTurntableButton.clicked.connect(self.openTurntable)

#     def openTurntable(self):
#         options = QFileDialog.Options()
#         fileName, _ = QFileDialog.getOpenFileName(self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mov);;All Files (*)", options=options)


# if __name__ == "__main__":
#     # create the application and the main window
#     app = QApplication(sys.argv)

#     # setup stylesheet
#     app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
#     # or in new API
#     app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt5"))

#     window = MainWindow()
#     window.show()

#     sys.exit(app.exec_())
