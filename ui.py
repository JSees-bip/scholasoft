"""
UI classes for the Scholasoft GABC editor.
No application logic or parser imports; main.py wires behavior.
"""

import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui


class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window. Has a menu bar (File, Edit, Tools)
    and a central text area. Menu actions emit signals; main.py connects them.
    """

    # Emitted when the user chooses File > Open (main.py shows dialog and parses).
    file_open_requested = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scholasoft")
        self.setMinimumSize(400, 300)
        self.resize(600, 400)

        self._build_menus()
        self._build_central_widget()

    def _build_menus(self):
        """Build the menu bar: File, Edit, Tools. Actions emit signals; main connects them."""
        menubar = self.menuBar()

        # --- File menu ---
        file_menu = menubar.addMenu("&File")

        self._open_action = QtGui.QAction("&Open...", self)
        self._open_action.setShortcut(QtGui.QKeySequence.StandardKey.Open)
        self._open_action.triggered.connect(self.file_open_requested.emit)
        file_menu.addAction(self._open_action)

        save_as_action = QtGui.QAction("Save &As...", self)
        save_as_action.setShortcut(QtGui.QKeySequence.StandardKey.SaveAs)
        file_menu.addAction(save_as_action)

        save_action = QtGui.QAction("&Save", self)
        save_action.setShortcut(QtGui.QKeySequence.StandardKey.Save)
        file_menu.addAction(save_action)

        # --- Edit menu ---
        edit_menu = menubar.addMenu("&Edit")

        undo_action = QtGui.QAction("&Undo", self)
        undo_action.setShortcut(QtGui.QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)

        redo_action = QtGui.QAction("&Redo", self)
        redo_action.setShortcut(QtGui.QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)

        # --- Tools menu (empty for now) ---
        menubar.addMenu("&Tools")

    def _build_central_widget(self):
        """Central area: read-only text. main.py sets content via set_display_text()."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self._text_display = QtWidgets.QPlainTextEdit()
        self._text_display.setReadOnly(True)
        self._text_display.setPlaceholderText("Open a .gabc file via File > Open...")
        self._text_display.setPlainText("Scholasoft\n\nUse File > Open... to load a .gabc file.")
        layout.addWidget(self._text_display)

    def set_display_text(self, text: str) -> None:
        """Set the central text area content. Called by main.py after parsing a file."""
        self._text_display.setPlainText(text)
