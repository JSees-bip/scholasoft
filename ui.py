"""
UI classes for the Scholasoft GABC editor.
No application logic or parser imports; main.py wires behavior.
"""

import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore
import PyQt6.QtGui as QtGui

from symbols import Clefs, Neumes


# Vertical grid: more slots = smaller slot_height = staff lines closer together (match font’s implicit staff spacing).
NUM_PITCH_SLOTS = 48
# Top staff line at this slot; staff centered in window. 4 lines -> slots (12,14,16,18).
STAFF_TOP_SLOT = 24
# Reduce spacing between staff lines by this many pixels total (neume/clef sizes stay based on unreduced span).
STAFF_LINE_SPACING_REDUCTION_PX = 32
# Nudge clef up so the C hole sits on the line (font glyph center vs visual center).
CLEF_NUDGE_UP_PX = 10
# Nudge font-rendered neumes up so they center like the fallback dots (font glyph vs visual center).
NEUME_NUDGE_UP_PX = 4
# Shift neumes down so they sit on the staff (reference: aveverum.svg has neumes in staff range).
NEUME_SLOT_OFFSET = -6


class StaffWidget(QtWidgets.QWidget):
    """
    Paints the staff (lines, clef, bars, syllables as note positions and text).
    Notes are aligned to a fixed grid so neumes sit on lines or in spaces.
    """

    def __init__(self, parent=None, clefs=None, neumes=None):
        super().__init__(parent)
        self._display = None
        self._clefs = clefs if clefs is not None else Clefs()
        self._neumes = neumes if neumes is not None else Neumes()
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
        staff_height = 180
        slot_height = staff_height / NUM_PITCH_SLOTS
        # Fixed staff span (same as draw) so staff is always centered
        line_count = max(2, min(5, int(getattr(self._display, "staff_line_count", 4))))
        staff_span_slots = max(2, 2 * (line_count - 1))
        staff_span_px = staff_span_slots * slot_height
        neume_size = max(40, int(staff_span_px * 0.65))
        clef_height = max(40, int(staff_span_px * 1.1))
        clef_width = max(32, int(clef_height * 0.5)) + 8
        elements = getattr(self._display, "elements", [])
        x = 50
        for el in elements:
            kind = el.get("type", "")
            if kind == "clef":
                x += clef_width
            elif kind == "bar":
                x += 20
            elif kind == "syllable":
                neumes = el.get("neumes", [])
                pitches = el.get("pitches", [])
                text = el.get("text", "")
                if neumes:
                    x += neume_size * len(neumes)
                elif pitches or text:
                    x += max(14 * len(pitches), 8 * len(text))
                else:
                    x += 12
                x += 12
        # Room for 28px + 1.5 staff spaces + lyrics line height
        slot_h = staff_height / NUM_PITCH_SLOTS
        text_space = 28 + int(1.5 * 2 * slot_h) + 24
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

    def _staff_line_slots(self) -> tuple[int, ...]:
        """
        Fixed staff line slots so the staff is always in the middle of the window.
        Top line = STAFF_TOP_SLOT; lines spaced by 2 slots (so spaces are at line_slot ± 1).
        """
        count = 4
        if self._display:
            count = getattr(self._display, "staff_line_count", 4)
            count = max(2, min(5, int(count)))
        return tuple(STAFF_TOP_SLOT - 2 * (count - 1 - i) for i in range(count))

    def _draw_staff(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        """Draw staff lines at fixed slots so the staff is always centered in the window."""
        slot_height_base = rect.height() / NUM_PITCH_SLOTS
        staff_slots = self._staff_line_slots()
        staff_span_slots = max(2, (staff_slots[-1] - staff_slots[0]) if staff_slots else 2)
        slot_height = slot_height_base - (STAFF_LINE_SPACING_REDUCTION_PX / staff_span_slots)
        def slot_to_y(slot: int) -> float:
            return rect.bottom() - (slot + 0.5) * slot_height

        pen = QtGui.QPen(QtCore.Qt.GlobalColor.black, 1)
        painter.setPen(pen)
        for slot in self._staff_line_slots():
            y = slot_to_y(slot)
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

    def _pitch_to_slot(self, pitch: int, clef_pitch: int = 2) -> int:
        """Map pitch index (0-12) to vertical slot. One slot per pitch so notes sit on lines or in spaces."""
        slot = STAFF_TOP_SLOT + NEUME_SLOT_OFFSET + (pitch - clef_pitch)
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
        """Draw clef, bars, and syllables. All positions referenced to clef; staff fixed in center."""
        elements = getattr(self._display, "elements", [])
        slot_height_base = rect.height() / NUM_PITCH_SLOTS
        staff_span_slots = max(2, (self._staff_line_slots()[-1] - self._staff_line_slots()[0]) if self._staff_line_slots() else 2)
        # Tighter line spacing: use reduced slot_height for positions (and staff lines in _draw_staff)
        slot_height = slot_height_base - (STAFF_LINE_SPACING_REDUCTION_PX / staff_span_slots)
        # Neume/clef size from unreduced span so glyphs stay the same size
        staff_span_px_for_glyphs = staff_span_slots * slot_height_base
        neume_height = max(40, int(staff_span_px_for_glyphs * 0.65))
        clef_height = max(40, int(staff_span_px_for_glyphs * 1.1))

        clef_pitch = getattr(self._display, "clef_pitch", 2) if self._display else 2
        staff_slots = self._staff_line_slots()

        def slot_to_y(slot: int) -> float:
            return rect.bottom() - (slot + 0.5) * slot_height

        def pitch_to_y(pitch: int) -> float:
            """Vertical center y for a pitch; same for font neumes and fallback dots."""
            return slot_to_y(self._pitch_to_slot(pitch, clef_pitch))

        y_top = slot_to_y(staff_slots[-1])
        y_bottom = slot_to_y(staff_slots[0])

        x = rect.left() + 30
        saved_font = painter.font()
        for el in elements:
            kind = el.get("type", "")
            if kind == "clef":
                clef_value = el.get("value", "c3")
                # Clef on top staff line; nudge up a few px so the C hole sits on the line.
                top_line_y = slot_to_y(staff_slots[-1])
                clef_center_y = top_line_y - CLEF_NUDGE_UP_PX
                dest_w = max(32, int(clef_height * 0.5))
                dest_h = clef_height
                dest_rect = QtCore.QRect(
                    int(x),
                    int(clef_center_y - dest_h / 2),
                    dest_w,
                    dest_h,
                )
                if not self._clefs.draw(painter, dest_rect, clef_value):
                    painter.setPen(QtCore.Qt.GlobalColor.black)
                    painter.drawText(int(x), int(clef_center_y), clef_value)
                painter.setFont(saved_font)
                x += dest_w + 8
            elif kind == "bar":
                pen = QtGui.QPen(QtCore.Qt.GlobalColor.black, 2)
                painter.setPen(pen)
                painter.drawLine(int(x), int(y_top), int(x), int(y_bottom))
                x += 20
            elif kind == "syllable":
                text = el.get("text", "")
                pitches = el.get("pitches", [])
                neumes = el.get("neumes", [])
                note_radius = 4
                syllable_x = x
                if neumes:
                    for neume in neumes:
                        shape = neume.get("shape", "punctum")
                        pits = neume.get("pitches", [])
                        if not pits:
                            continue
                        first_pitch_y = pitch_to_y(pits[0])
                        nw = neume_height
                        nh = neume_height
                        # Apply nudge so font glyph centers like fallback dots.
                        center_y = first_pitch_y - NEUME_NUDGE_UP_PX
                        dest_rect = QtCore.QRect(
                            int(x),
                            int(center_y - nh / 2),
                            nw,
                            nh,
                        )
                        intervals_arg = neume.get("intervals")
                        if self._neumes.draw(painter, dest_rect, shape, intervals=intervals_arg):
                            x += nw
                        else:
                            print(f"[ui] fallback dots shape={shape!r} intervals={intervals_arg} pitches={pits}")
                            for p in pits:
                                py = pitch_to_y(p)
                                painter.setBrush(QtCore.Qt.GlobalColor.black)
                                painter.setPen(QtCore.Qt.GlobalColor.black)
                                painter.drawEllipse(
                                    int(x - note_radius), int(py - note_radius),
                                    note_radius * 2, note_radius * 2,
                                )
                                x += 14
                        painter.setFont(saved_font)
                else:
                    for p in pitches:
                        py = pitch_to_y(p)
                        painter.setBrush(QtCore.Qt.GlobalColor.black)
                        painter.setPen(QtCore.Qt.GlobalColor.black)
                        painter.drawEllipse(
                            int(x - note_radius), int(py - note_radius),
                            note_radius * 2, note_radius * 2,
                        )
                        x += 14
                syllable_width = x - syllable_x
                if text:
                    painter.setPen(QtCore.Qt.GlobalColor.black)
                    lyrics_font = painter.font()
                    lyrics_font.setPointSize(max(lyrics_font.pointSize(), 14))
                    painter.setFont(lyrics_font)
                    # One and a half staff spaces below the bottom staff line
                    staff_space = 2 * slot_height
                    text_y = y_bottom + 28 + 1.5 * staff_space
                    text_center_x = syllable_x + syllable_width / 2
                    metrics = QtGui.QFontMetrics(lyrics_font)
                    text_width = metrics.horizontalAdvance(text)
                    text_x = text_center_x - text_width / 2
                    painter.drawText(int(text_x), int(text_y), text)
                    painter.setFont(saved_font)
                if not pitches and text:
                    x += 8 * len(text)
                x += 12


class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window. Has a menu bar (File, Edit, Tools)
    and a central area: either raw text (verbose) or staff plot.
    """

    file_open_requested = QtCore.pyqtSignal()

    def __init__(self, clefs=None, neumes=None):
        super().__init__()
        self.setWindowTitle("Scholasoft")
        self.setMinimumSize(400, 300)
        self.resize(600, 400)

        self._clefs = clefs
        self._neumes = neumes
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
        self._staff_widget = StaffWidget(clefs=self._clefs, neumes=self._neumes)
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
