"""
UI classes for the Scholasoft GABC editor.
No application logic or parser imports; main.py wires behavior.
"""

import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui


# Vertical grid: 13 slots for pitches a-m (0-12). Staff lines sit on slots 2,4,6,8 (4-line staff).
# Clef c3 means pitch c (index 2) is on line 3 (slot 6), so slot = pitch + 4.
NUM_PITCH_SLOTS = 13
STAFF_LINE_SLOTS = (2, 4, 6, 8)  # 4-line staff: lines at these slot indices (0 = bottom)


class StaffWidget(QtWidgets.QWidget):
    """
    Paints the staff (lines, clef, bars, syllables as note positions and text).
    Notes are aligned to a fixed grid so neumes sit on lines or in spaces.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display = None
        self.setMinimumSize(400, 200)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )

    def set_display(self, display) -> None:
        """Set the display model (from GabcStaff.build_display). None to clear."""
        self._display = display
        if display:
            w, h = self._content_size()
            self.setMinimumSize(max(400, w), max(200, h))
        else:
            self.setMinimumSize(400, 200)
        self.update()

    def _content_size(self) -> tuple[int, int]:
        """Return (width, height) needed to draw all elements for scrolling."""
        if not self._display:
            return (400, 200)
        elements = getattr(self._display, "elements", [])
        x = 50
        for el in elements:
            kind = el.get("type", "")
            if kind == "clef":
                x += 40
            elif kind == "bar":
                x += 20
            elif kind == "syllable":
                pitches = el.get("pitches", [])
                text = el.get("text", "")
                x += max(14 * len(pitches), 8 * len(text)) if (pitches or text) else 12
                x += 12
        staff_height = 180
        text_space = 30
        return (int(x) + 40, int(staff_height + text_space + 40))

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(20, 20, -20, -20)
        if rect.width() <= 0 or rect.height() <= 0:
            painter.end()
            return
        if not self._display:
            self._draw_welcome(painter, rect)
            painter.end()
            return
        self._draw_staff(painter, rect)
        self._draw_elements(painter, rect)
        painter.end()

    def _draw_welcome(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        """Draw welcome text when no file is loaded (verbose = False)."""
        painter.setPen(QtCore.Qt.GlobalColor.darkGray)
        font = painter.font()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, "Scholasoft")
        font.setPointSize(12)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(
            rect.adjusted(0, 40, 0, 0),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            "Use File > Open... to load a .gabc file.",
        )

    def _draw_staff(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        """Draw staff lines on a fixed grid so neumes align with lines/spaces."""
        slot_height = rect.height() / NUM_PITCH_SLOTS
        # Slot 0 at bottom, slot 12 at top
        def slot_to_y(slot: int) -> float:
            return rect.bottom() - (slot + 0.5) * slot_height

        pen = QtGui.QPen(QtCore.Qt.GlobalColor.black, 1)
        painter.setPen(pen)
        for slot in STAFF_LINE_SLOTS:
            y = slot_to_y(slot)
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

    def _pitch_to_slot(self, pitch: int, pitch_center: float | None = None) -> int:
        """Map pitch index (0-12) to vertical slot. Staff is centered on pitch_center so neumes align with lines."""
        if pitch_center is None:
            pitch_center = 5.0  # default: center staff on middle of range
        # Middle of staff (slot 6) = pitch_center; slot 0 at bottom, 12 at top
        slot = 6 + (pitch - pitch_center)
        return min(max(int(round(slot)), 0), NUM_PITCH_SLOTS - 1)

    def _pitch_range_from_display(self) -> tuple[float, float]:
        """Min and max pitch in display elements; (5, 5) if none (so center stays 5)."""
        elements = getattr(self._display, "elements", [])
        pits = []
        for el in elements:
            if el.get("type") == "syllable":
                pits.extend(el.get("pitches", []))
        if not pits:
            return (5.0, 5.0)
        return (float(min(pits)), float(max(pits)))

    def _draw_elements(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        """Draw clef, bars, and syllables; neumes snap to staff grid."""
        elements = getattr(self._display, "elements", [])
        slot_height = rect.height() / NUM_PITCH_SLOTS
        min_p, max_p = self._pitch_range_from_display()
        pitch_center = (min_p + max_p) / 2.0

        def slot_to_y(slot: int) -> float:
            return rect.bottom() - (slot + 0.5) * slot_height

        def pitch_to_y(pitch: int) -> float:
            return slot_to_y(self._pitch_to_slot(pitch, pitch_center))

        y_top = slot_to_y(STAFF_LINE_SLOTS[-1])
        y_bottom = slot_to_y(STAFF_LINE_SLOTS[0])

        x = rect.left() + 30
        for el in elements:
            kind = el.get("type", "")
            if kind == "clef":
                painter.setPen(QtCore.Qt.GlobalColor.black)
                mid_y = (y_top + y_bottom) / 2
                painter.drawText(int(x), int(mid_y), el.get("value", "c3"))
                x += 40
            elif kind == "bar":
                pen = QtGui.QPen(QtCore.Qt.GlobalColor.black, 2)
                painter.setPen(pen)
                painter.drawLine(int(x), int(y_top), int(x), int(y_bottom))
                x += 20
            elif kind == "syllable":
                text = el.get("text", "")
                pitches = el.get("pitches", [])
                note_radius = 4
                syllable_x = x
                for p in pitches:
                    py = pitch_to_y(p)
                    painter.setBrush(QtCore.Qt.GlobalColor.black)
                    painter.setPen(QtCore.Qt.GlobalColor.black)
                    painter.drawEllipse(
                        int(x - note_radius), int(py - note_radius),
                        note_radius * 2, note_radius * 2,
                    )
                    x += 14
                if text:
                    painter.setPen(QtCore.Qt.GlobalColor.black)
                    text_y = y_bottom + 18
                    painter.drawText(int(syllable_x), int(text_y), text)
                if not pitches and text:
                    x += 8 * len(text)
                x += 12


class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window. Has a menu bar (File, Edit, Tools)
    and a central area: either raw text (verbose) or staff plot.
    """

    file_open_requested = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scholasoft")
        self.setMinimumSize(400, 300)
        self.resize(600, 400)

        # Verbose: show raw parsed text when True, staff plot when False.
        self._verbose = False
        self._display_model = None

        self._build_menus()
        self._build_central_widget()

    @property
    def verbose(self) -> bool:
        """Whether to show raw parsed text (True) or staff plot (False). main.py reads this."""
        return self._verbose

    def _build_menus(self):
        menubar = self.menuBar()

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

        edit_menu = menubar.addMenu("&Edit")
        undo_action = QtGui.QAction("&Undo", self)
        undo_action.setShortcut(QtGui.QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        redo_action = QtGui.QAction("&Redo", self)
        redo_action.setShortcut(QtGui.QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)

        tools_menu = menubar.addMenu("&Tools")
        self._verbose_action = QtGui.QAction("Toggle &verbose", self)
        self._verbose_action.triggered.connect(self._on_toggle_verbose)
        tools_menu.addAction(self._verbose_action)

    def _build_central_widget(self):
        """Stack: index 0 = staff in scroll area, index 1 = text (verbose)."""
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self._stack = QtWidgets.QStackedWidget()
        self._staff_widget = StaffWidget()
        self._staff_scroll = QtWidgets.QScrollArea()
        self._staff_scroll.setWidget(self._staff_widget)
        self._staff_scroll.setWidgetResizable(True)
        self._staff_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._staff_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._stack.addWidget(self._staff_scroll)

        self._text_display = QtWidgets.QPlainTextEdit()
        self._text_display.setReadOnly(True)
        self._text_display.setPlaceholderText("Open a .gabc file via File > Open...")
        self._text_display.setPlainText("Scholasoft\n\nUse File > Open... to load a .gabc file.")
        self._stack.addWidget(self._text_display)

        layout.addWidget(self._stack)
        self._update_verbose_view()

    def _on_toggle_verbose(self):
        self._verbose = not self._verbose
        self._update_verbose_view()

    def _update_verbose_view(self):
        if self._verbose:
            self._stack.setCurrentWidget(self._text_display)
        else:
            self._stack.setCurrentWidget(self._staff_scroll)

    def set_display_text(self, text: str) -> None:
        """Set the raw text (for debugging when verbose is on)."""
        self._text_display.setPlainText(text)

    def set_display_model(self, display) -> None:
        """Set the staff display model (from GabcStaff.build_display)."""
        self._display_model = display
        self._staff_widget.set_display(display)
