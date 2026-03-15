"""
Gregorian chant symbols using the Gregorio-project font (greciliae).
Reads the TTF from lib/gregorio-project/fonts/ (read-only), builds a
glyph-name→Unicode mapping with fontTools, and draws clefs/neumes via QFont.
Falls back to UI text/circles when the font is missing or a glyph is unknown.
"""

from __future__ import annotations

import os
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QFont, QFontDatabase, QPainter

# Cache glyph name → Unicode for a given TTF path (avoid re-parsing).
_glyph_cache: dict[str, dict[str, int]] = {}

# Shared Gregorio font load (family name and name→unicode map). Loaded once.
_gregorio_load_attempted = False
_gregorio_font_family: str | None = None
_gregorio_name_to_unicode: dict[str, int] = {}

def _gregorio_font_path() -> str:
    """
    Path to greciliae.ttf. Prefer .symbols/greciliae.ttf (build output);
    else lib/gregorio-project/fonts/greciliae.ttf (read-only).
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    in_symbols = os.path.join(project_root, ".symbols", "greciliae.ttf")
    if os.path.isfile(in_symbols):
        return in_symbols
    return os.path.join(project_root, "lib", "gregorio-project", "fonts", "greciliae.ttf")


def _glyph_name_to_unicode_map(ttf_path: str) -> dict[str, int]:
    """
    Build glyph name → Unicode scalar from the TTF using fontTools.
    Cached per path. Returns empty dict if file missing or on error.
    """
    if ttf_path in _glyph_cache:
        return _glyph_cache[ttf_path]
    if not os.path.isfile(ttf_path):
        _glyph_cache[ttf_path] = {}
        return {}
    try:
        from fontTools.ttLib import TTFont

        font = TTFont(ttf_path)
        cmap = font.getBestCmap()
        font.close()
        # cmap: unicode (int) → glyph name (str)
        name_to_unicode = {name: code for code, name in (cmap or {}).items()}
        _glyph_cache[ttf_path] = name_to_unicode
        return name_to_unicode
    except Exception:
        _glyph_cache[ttf_path] = {}
        return {}


def _load_gregorio_font_once() -> tuple[str | None, dict[str, int]]:
    """Load greciliae once; return (font family name, glyph name→unicode map)."""
    global _gregorio_load_attempted, _gregorio_font_family, _gregorio_name_to_unicode
    if _gregorio_load_attempted:
        return _gregorio_font_family, _gregorio_name_to_unicode
    _gregorio_load_attempted = True
    path = _gregorio_font_path()
    if not os.path.isfile(path):
        return None, {}
    _gregorio_name_to_unicode = _glyph_name_to_unicode_map(path)
    if not _gregorio_name_to_unicode:
        return None, {}
    font_id = QFontDatabase.addApplicationFont(path)
    if font_id >= 0:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            _gregorio_font_family = families[0]
    return _gregorio_font_family, _gregorio_name_to_unicode


# GABC clef value → Gregorio glyph name (from gregoriotex-chars.tex).
# Flatted clefs (cb*, fb*) use normal clef + Flat glyph so the accidental looks correct.
CLEF_VALUE_TO_GLYPH: dict[str, str] = {
    "c2": "CClef",
    "c3": "CClef",
    "c4": "CClef",
    "cb2": "CClef",
    "cb3": "CClef",
    "cb4": "CClef",
    "f3": "FClef",
    "f4": "FClef",
    "f5": "FClef",
    "fb3": "FClef",
    "fb4": "FClef",
}
FLAT_GLYPH_NAME = "Flat"

# Interval index 1..5 → ambitus suffix (matches squarize AMBITUS).
AMBITUS_SUFFIX: dict[int, str] = {
    1: "One",
    2: "Two",
    3: "Three",
    4: "Four",
    5: "Five",
}

# Logical neume name → Gregorio glyph name (basic set; names from gregorio squarize).
# For multi-note neumes the font uses ambitus suffixes + "Nothing" (e.g. FlexusOneNothing).
NEUME_NAME_TO_GLYPH: dict[str, str] = {
    "punctum": "Punctum",
    "virga": "Virga",
    "podatus": "PesQuadratumLongqueue",
    "clivis": "Flexus",
    "torculus": "Torculus",
    "porrectus": "Porrectus",
    "climacus": "Climacus",
    "bistropha": "Stropha",
    "tristropha": "Stropha",
    "pressus": "Stropha",
    "quilisma": "Quilisma",
    "scandicus": "Scandicus",
    "salicus": "Salicus",
    "liquescent": "DescendensPunctumInclinatum",
}

# Fallback base names when the primary base has no glyph (e.g. greciliae may have PesOneNothing but not PesQuadratumLongqueueOneNothing).
NEUME_NAME_FALLBACK_BASES: dict[str, list[str]] = {
    "podatus": ["Pes"],  # try PesOneNothing etc. if PesQuadratumLongqueue not in font
}


class Clefs:
    """
    Clef rendering using the Gregorio greciliae font.
    Maps GABC clef values (e.g. 'c3', 'f4') to font glyphs and draws with QFont.
    """

    # Nominal draw size for layout (UI uses these for dest_rect).
    TILE_WIDTH = 40
    TILE_HEIGHT = 80

    def __init__(self) -> None:
        self._family, self._name_to_unicode = _load_gregorio_font_once()

    def draw(
        self,
        painter: QPainter,
        dest_rect: QRect,
        clef_value: str,
    ) -> bool:
        """
        Draw the clef glyph for clef_value into dest_rect.
        For flatted clefs (cb*, fb*), draws the normal clef then the proper Flat accidental.
        Returns True if drawn, False if fallback should be used (e.g. text).
        """
        if self._family is None or not self._name_to_unicode:
            return False
        key = (clef_value or "c3").strip().lower()
        glyph_name = CLEF_VALUE_TO_GLYPH.get(key, CLEF_VALUE_TO_GLYPH.get("c3", "CClef"))
        codepoint = self._name_to_unicode.get(glyph_name)
        if codepoint is None:
            return False
        font = QFont(self._family)
        font.setPixelSize(max(dest_rect.height(), 1))
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.black)
        has_flat = key in ("cb2", "cb3", "cb4", "fb3", "fb4")
        if has_flat:
            # Split rect: clef in left portion, Flat accidental in right portion
            w = dest_rect.width()
            clef_w = max(int(w * 0.6), w - 24)
            clef_rect = QRect(dest_rect.left(), dest_rect.top(), clef_w, dest_rect.height())
            flat_rect = QRect(dest_rect.left() + clef_w, dest_rect.top(), w - clef_w, dest_rect.height())
            painter.drawText(
                clef_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                chr(codepoint),
            )
            flat_cp = self._name_to_unicode.get(FLAT_GLYPH_NAME)
            if flat_cp is not None:
                font_flat = QFont(self._family)
                font_flat.setPixelSize(max(flat_rect.height(), 1))
            else:
                flat_cp = 0x266D  # Unicode MUSIC FLAT SIGN ♭
                font_flat = QFont(painter.font())
                font_flat.setPixelSize(max(flat_rect.height(), 1))
            painter.setFont(font_flat)
            painter.drawText(
                flat_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                chr(flat_cp),
            )
            painter.setFont(font)
        else:
            painter.drawText(
                dest_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                chr(codepoint),
            )
        return True

    def draw_flat(
        self,
        painter: QPainter,
        dest_rect: QRect,
    ) -> bool:
        """
        Draw only the flat accidental into dest_rect (for note-level flats).
        Returns True if drawn.
        """
        if self._family is None or not self._name_to_unicode:
            return False
        flat_cp = self._name_to_unicode.get(FLAT_GLYPH_NAME)
        if flat_cp is not None:
            font = QFont(self._family)
            font.setPixelSize(max(dest_rect.height(), 1))
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(
                dest_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                chr(flat_cp),
            )
            return True
        flat_cp = 0x266D  # Unicode MUSIC FLAT SIGN ♭
        font = QFont(painter.font())
        font.setPixelSize(max(dest_rect.height(), 1))
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(
            dest_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            chr(flat_cp),
        )
        return True


class Neumes:
    """
    Neume rendering using the Gregorio greciliae font.
    Maps logical neume names to font glyph names and draws with QFont.
    """

    # Nominal draw size for layout.
    TILE_WIDTH = 48
    TILE_HEIGHT = 48

    def __init__(self) -> None:
        self._family, self._name_to_unicode = _load_gregorio_font_once()

    def draw(
        self,
        painter: QPainter,
        dest_rect: QRect,
        neume_name: str,
        intervals: list[int] | None = None,
    ) -> bool:
        """
        Draw the neume glyph for neume_name into dest_rect.
        If intervals is provided (1 or 2 ints in 1..5), try ambitus-suffixed glyph names
        (e.g. FlexusOne, ScandicusOneOne) before falling back to base name. Climacus has
        no font glyph and returns False.
        Returns True if drawn, False if fallback should be used.
        """
        if self._family is None or not self._name_to_unicode:
            return False
        key = (neume_name or "punctum").strip().lower()
        if key == "climacus":
            # Gregorio font has no Climacus glyph; UI draws fallback dots.
            return False
        if key == "compound":
            # 4+ note group with no single glyph; UI will draw one dot per pitch
            return False
        # Bistropha/tristropha: try bare "Stropha" first (font has it; StrophaOneNothing is missing)
        if key in ("bistropha", "tristropha", "pressus") and self._name_to_unicode.get("Stropha") is not None:
            codepoint = self._name_to_unicode["Stropha"]
            font = QFont(self._family)
            font.setPixelSize(max(dest_rect.height(), 1))
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(
                dest_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                chr(codepoint),
            )
            return True
        base_glyph = NEUME_NAME_TO_GLYPH.get(key)
        if base_glyph is None:
            return False
        # Build list of base names to try: primary + any fallbacks for this neume type
        bases_to_try: list[str] = [base_glyph]
        for fb in NEUME_NAME_FALLBACK_BASES.get(key, []):
            if fb not in bases_to_try:
                bases_to_try.append(fb)
        glyph_name: str | None = None
        candidates_tried: list[str] = []
        if intervals:
            clamped = [
                max(1, min(5, i)) for i in intervals[:2]
            ]
            suffixes = [AMBITUS_SUFFIX.get(i, "One") for i in clamped]
            for base in bases_to_try:
                if len(suffixes) == 1:
                    c1 = base + suffixes[0]
                    c2 = c1 + "Nothing"
                    candidates_tried.extend([c1, c2])
                    if self._name_to_unicode.get(c1) is not None:
                        glyph_name = c1
                        break
                    if self._name_to_unicode.get(c2) is not None:
                        glyph_name = c2
                        break
                elif len(suffixes) >= 2:
                    c1 = base + suffixes[0] + suffixes[1]
                    c2 = c1 + "Nothing"
                    candidates_tried.extend([c1, c2])
                    if self._name_to_unicode.get(c1) is not None:
                        glyph_name = c1
                        break
                    if self._name_to_unicode.get(c2) is not None:
                        glyph_name = c2
                        break
        if glyph_name is None:
            glyph_name = base_glyph
            candidates_tried.append(base_glyph)
        codepoint = self._name_to_unicode.get(glyph_name)
        if codepoint is None:
            print(f"[symbols] miss shape={key!r} intervals={intervals} tried={candidates_tried}")
            return False
        font = QFont(self._family)
        font.setPixelSize(max(dest_rect.height(), 1))
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(
            dest_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            chr(codepoint),
        )
        return True

    def draw_flat(
        self,
        painter: QPainter,
        dest_rect: QRect,
    ) -> bool:
        """
        Draw the flat accidental into dest_rect (e.g. before a neume).
        Uses the same font as neumes; falls back to Unicode ♭ if the glyph is missing.
        Returns True if drawn.
        """
        if self._family is None or not self._name_to_unicode:
            return False
        flat_cp = self._name_to_unicode.get(FLAT_GLYPH_NAME)
        if flat_cp is not None:
            font = QFont(self._family)
            font.setPixelSize(max(dest_rect.height(), 1))
            painter.setFont(font)
            painter.setPen(Qt.GlobalColor.black)
            painter.drawText(
                dest_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                chr(flat_cp),
            )
            return True
        flat_cp = 0x266D  # Unicode MUSIC FLAT SIGN ♭
        font = QFont(painter.font())
        font.setPixelSize(max(dest_rect.height(), 1))
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(
            dest_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            chr(flat_cp),
        )
        return True
