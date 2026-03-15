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
STAFF_LINE_SPACING_REDUCTION_PX = 20
# Nudge clef up so the C hole sits on the line (font glyph center vs visual center).
CLEF_NUDGE_UP_PX = 3
# Nudge font-rendered neumes up so they center like the fallback dots (font glyph vs visual center).
NEUME_NUDGE_UP_PX = 2
# Shift neumes down so they sit on the staff (reference: aveverum.svg has neumes in staff range).
NEUME_SLOT_OFFSET = -6
# Episema (note held longer): horizontal line drawn this many px above note center; half-length of line.
EPISEMA_OFFSET_PX = 8
EPISEMA_HALF_LEN_PX = 5
# Vertical gap between wrapped systems (staff + lyrics of one line to next staff).
SYSTEM_GAP_PX = 32
# Reference height used only to compute slot_height for wrapped systems (keeps staff spacing readable; not a global layout change).
WRAPPED_SYSTEM_REFERENCE_HEIGHT = 520


def _draw_rhombus(painter: QtGui.QPainter, center_x: int, center_y: int, size: int) -> None:
    """Draw a filled diamond (rhombus) for climacus descending notes. size = approximate width/height."""
    half = max(2, size // 2)
    points = [
        QtCore.QPoint(center_x, center_y - half),
        QtCore.QPoint(center_x + half, center_y),
        QtCore.QPoint(center_x, center_y + half),
        QtCore.QPoint(center_x - half, center_y),
    ]
    painter.setBrush(QtCore.Qt.GlobalColor.black)
    painter.setPen(QtCore.Qt.GlobalColor.black)
    painter.drawPolygon(QtGui.QPolygon(points))


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
            _, h = self._content_size(400)
            self.setMinimumSize(400, max(200, h))
        else:
            self.setMinimumSize(400, 200)
        self.update()

    def _glyph_sizes(self):
        """Return (staff_height, neume_size, clef_width, lyrics_space) for layout/wrap."""
        staff_height = 180
        slot_height = staff_height / NUM_PITCH_SLOTS
        line_count = max(2, min(5, int(getattr(self._display, "staff_line_count", 4))))
        staff_span_slots = max(2, 2 * (line_count - 1))
        staff_span_px = staff_span_slots * slot_height
        neume_size = max(40, int(staff_span_px * 0.65))
        clef_height = max(40, int(staff_span_px * 1.1))
        clef_width = max(32, int(clef_height * 0.5)) + 8
        slot_h = staff_height / NUM_PITCH_SLOTS
        lyrics_space = 28 + int(1.5 * 2 * slot_h) + 24
        return staff_height, neume_size, clef_width, lyrics_space

    def _element_width(self, el: dict, neume_size: int, clef_width: int) -> int:
        """Width in px for one element (clef, bar, or syllable). Matches draw spacing."""
        kind = el.get("type", "")
        if kind == "clef":
            return clef_width + 8
        if kind == "bar":
            return 20
        if kind == "syllable":
            neumes = el.get("neumes", [])
            pitches = el.get("pitches", [])
            text = el.get("text", "")
            if neumes:
                w = neume_size * len(neumes)
                flat_extra = max(14, int(neume_size * 0.4))
                for n in neumes:
                    if n.get("accidental_before") == "flat":
                        w += flat_extra
            elif pitches or text:
                w = max(14 * len(pitches), 8 * len(text))
            else:
                w = 12
            return w + 12
        return 0

    def _wrap_elements(self, available_width: int) -> list[list[int]]:
        """
        Return list of rows; each row is a list of element indices that fit in available_width.
        Break only between elements. First element of first row is always 0; wrapped rows get a clef drawn at start (no extra index).
        """
        if not self._display:
            return []
        staff_height, neume_size, clef_width, _ = self._glyph_sizes()
        elements = getattr(self._display, "elements", [])
        if not elements:
            return []
        # left/right margin and padding
        content_width = max(100, available_width - 40 - 40)
        rows: list[list[int]] = []
        current_row: list[int] = []
        row_x = 30
        for i, el in enumerate(elements):
            w = self._element_width(el, neume_size, clef_width)
            if current_row and row_x + w > content_width:
                rows.append(current_row)
                current_row = []
                row_x = 30 + clef_width + 8
            current_row.append(i)
            row_x += w
        if current_row:
            rows.append(current_row)
        return rows

    def _content_size(self, available_width: int | None = None) -> tuple[int, int]:
        """Return (width, height). If available_width given, use wrap and return wrapped height; else single line."""
        if not self._display:
            return (400, 200)
        _, _, _, lyrics_space = self._glyph_sizes()
        if available_width is not None and available_width > 0:
            _, staff_span_px = self._wrapped_slot_height_and_span()
            one_system_height = staff_span_px + lyrics_space + SYSTEM_GAP_PX
            rows = self._wrap_elements(available_width)
            if not rows:
                return (400, max(200, int(one_system_height + 40)))
            total_height = len(rows) * one_system_height - SYSTEM_GAP_PX + 40
            return (min(400, available_width), max(200, int(total_height)))
        staff_height, _, _, _ = self._glyph_sizes()
        one_system_height = staff_height + lyrics_space + SYSTEM_GAP_PX
        elements = getattr(self._display, "elements", [])
        _, neume_size, clef_width, _ = self._glyph_sizes()
        x = 50
        for el in elements:
            x += self._element_width(el, neume_size, clef_width)
        return (int(x) + 40, max(200, int(one_system_height + 40)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._display and event.size().width() > 0:
            _, h = self._content_size(event.size().width())
            self.setMinimumHeight(max(200, h))

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
        rows = self._wrap_elements(rect.width())
        _, _, _, lyrics_space = self._glyph_sizes()
        slot_height, staff_span_px = self._wrapped_slot_height_and_span()
        one_system_height = staff_span_px + lyrics_space + SYSTEM_GAP_PX
        clef_value = getattr(self._display, "clef_value", "c3") or "c3"
        for r, indices in enumerate(rows):
            y_base = rect.top() + r * one_system_height
            row_staff_rect = QtCore.QRect(rect.left(), int(y_base), rect.width(), int(staff_span_px))
            self._draw_staff(painter, row_staff_rect, slot_height)
            self._draw_elements_row(
                painter, rect.width(), row_staff_rect, indices,
                r > 0, clef_value, lyrics_space, slot_height,
            )
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

    def _wrapped_slot_height_and_span(self) -> tuple[float, float]:
        """Slot height and staff span in px for one wrapped system (fixed reference; keeps spacing readable)."""
        staff_slots = self._staff_line_slots()
        staff_span_slots = max(2, (staff_slots[-1] - staff_slots[0]) if staff_slots else 2)
        slot_height_base = WRAPPED_SYSTEM_REFERENCE_HEIGHT / NUM_PITCH_SLOTS
        slot_height = slot_height_base - (STAFF_LINE_SPACING_REDUCTION_PX / staff_span_slots)
        staff_span_px = staff_span_slots * slot_height
        return slot_height, staff_span_px

    def _draw_staff(self, painter: QtGui.QPainter, row_rect: QtCore.QRect, slot_height: float):
        """Draw staff lines in one row's band. Map staff slots into row_rect so the staff fits (bottom line at bottom of row)."""
        staff_slots = self._staff_line_slots()
        bottom_slot = staff_slots[0] if staff_slots else STAFF_TOP_SLOT - 6

        def slot_to_y(slot: int) -> float:
            return row_rect.bottom() - (slot - bottom_slot + 0.5) * slot_height

        pen = QtGui.QPen(QtCore.Qt.GlobalColor.black, 1)
        painter.setPen(pen)
        for slot in staff_slots:
            y = slot_to_y(slot)
            painter.drawLine(row_rect.left(), int(y), row_rect.right(), int(y))

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

    def _draw_elements_row(
        self,
        painter: QtGui.QPainter,
        content_width: int,
        row_staff_rect: QtCore.QRect,
        indices: list[int],
        draw_clef_at_start: bool,
        clef_value: str,
        lyrics_space: int,
        slot_height: float,
    ):
        """Draw one row's elements (clef optional at start, then bars/syllables). Uses passed slot_height so spacing is unchanged when wrapping."""
        elements = getattr(self._display, "elements", [])
        staff_slots = self._staff_line_slots()
        staff_height, _, _, _ = self._glyph_sizes()
        staff_span_slots = max(2, (staff_slots[-1] - staff_slots[0]) if staff_slots else 2)
        slot_height_base = staff_height / NUM_PITCH_SLOTS
        staff_span_px_for_glyphs = staff_span_slots * slot_height_base
        neume_height = max(40, int(staff_span_px_for_glyphs * 0.65))
        clef_height = max(40, int(staff_span_px_for_glyphs * 1.1))
        clef_pitch = getattr(self._display, "clef_pitch", 2) if self._display else 2
        bottom_slot = staff_slots[0] if staff_slots else (STAFF_TOP_SLOT - 6)

        def slot_to_y(slot: int) -> float:
            return row_staff_rect.bottom() - (slot - bottom_slot + 0.5) * slot_height

        def pitch_to_y(pitch: int) -> float:
            return slot_to_y(self._pitch_to_slot(pitch, clef_pitch))

        y_top = slot_to_y(staff_slots[-1])
        y_bottom = slot_to_y(staff_slots[0])
        staff_space = 2 * slot_height
        text_y_base = row_staff_rect.bottom() + 28 + 1.5 * staff_space

        x = row_staff_rect.left() + 30
        saved_font = painter.font()
        if draw_clef_at_start:
            top_line_y = slot_to_y(staff_slots[-1])
            clef_center_y = top_line_y - CLEF_NUDGE_UP_PX
            dest_w = max(32, int(clef_height * 0.5))
            dest_h = clef_height
            dest_rect = QtCore.QRect(
                int(x), int(clef_center_y - dest_h / 2), dest_w, dest_h,
            )
            if not self._clefs.draw(painter, dest_rect, clef_value):
                painter.setPen(QtCore.Qt.GlobalColor.black)
                painter.drawText(int(x), int(clef_center_y), clef_value)
            painter.setFont(saved_font)
            x += dest_w + 8
        for i in indices:
            el = elements[i]
            kind = el.get("type", "")
            if kind == "clef":
                cv = el.get("value", "c3")
                top_line_y = slot_to_y(staff_slots[-1])
                clef_center_y = top_line_y - CLEF_NUDGE_UP_PX
                dest_w = max(32, int(clef_height * 0.5))
                dest_h = clef_height
                dest_rect = QtCore.QRect(
                    int(x), int(clef_center_y - dest_h / 2), dest_w, dest_h,
                )
                if not self._clefs.draw(painter, dest_rect, cv):
                    painter.setPen(QtCore.Qt.GlobalColor.black)
                    painter.drawText(int(x), int(clef_center_y), cv)
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
                        episema_at = neume.get("episema_at") or []
                        if not pits:
                            continue
                        first_pitch_y = pitch_to_y(pits[0])
                        nw, nh = neume_height, neume_height
                        center_y = first_pitch_y - NEUME_NUDGE_UP_PX
                        if neume.get("accidental_before") == "flat":
                            flat_w = max(14, int(neume_height * 0.4))
                            flat_rect = QtCore.QRect(int(x), int(center_y - nh // 2), flat_w, nh)
                            self._neumes.draw_flat(painter, flat_rect)
                            painter.setFont(saved_font)
                            x += flat_w
                        dest_rect = QtCore.QRect(
                            int(x), int(center_y - nh / 2), nw, nh,
                        )
                        intervals_arg = neume.get("intervals")
                        if self._neumes.draw(painter, dest_rect, shape, intervals=intervals_arg):
                            x += nw
                        else:
                            # Climacus (3 descending): virga + 2 rhombi (inclinatum); fallback to drawn diamond if no glyph
                            if shape == "climacus" and len(pits) == 3:
                                for i, p in enumerate(pits):
                                    py = pitch_to_y(p)
                                    cy = py - NEUME_NUDGE_UP_PX
                                    rw, rh = int(neume_height * 0.5), neume_height
                                    nr = QtCore.QRect(int(x), int(cy - rh / 2), rw, rh)
                                    if i == 0:
                                        self._neumes.draw(painter, nr, "virga")
                                    else:
                                        if not self._neumes.draw(painter, nr, "liquescent"):
                                            _draw_rhombus(painter, int(x + rw / 2), int(cy), note_radius * 2)
                                    if i in episema_at:
                                        cx = int(x + rw / 2)
                                        painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black, 2))
                                        painter.drawLine(cx - EPISEMA_HALF_LEN_PX, int(cy - EPISEMA_OFFSET_PX), cx + EPISEMA_HALF_LEN_PX, int(cy - EPISEMA_OFFSET_PX))
                                        painter.setPen(QtCore.Qt.GlobalColor.black)
                                    x += 14
                            else:
                                # Compound (4+ notes): fallback dots; shift down one slot so they align with staff
                                slot_nudge = slot_height if shape == "compound" else 0
                                for idx, p in enumerate(pits):
                                    py = pitch_to_y(p) + slot_nudge
                                    painter.setBrush(QtCore.Qt.GlobalColor.black)
                                    painter.setPen(QtCore.Qt.GlobalColor.black)
                                    painter.drawEllipse(
                                        int(x - note_radius), int(py - note_radius),
                                        note_radius * 2, note_radius * 2,
                                    )
                                    if idx in episema_at:
                                        painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.black, 2))
                                        painter.drawLine(int(x - EPISEMA_HALF_LEN_PX), int(py - EPISEMA_OFFSET_PX), int(x + EPISEMA_HALF_LEN_PX), int(py - EPISEMA_OFFSET_PX))
                                        painter.setPen(QtCore.Qt.GlobalColor.black)
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
                    text_y = text_y_base
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
        self._staff_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
