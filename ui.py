"""
UI classes for the Scholasoft GABC editor.
"""

import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore


class MainWindow(QtWidgets.QMainWindow):
    """Main application window. Shows the program name for now."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scholasoft")
        self.setMinimumSize(400, 300)
        self.resize(600, 400)

        # Central widget: a label with the program name
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        title = QtWidgets.QLabel("Scholasoft")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
