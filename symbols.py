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
CLEF_VALUE_TO_GLYPH: dict[str, str] = {
    "c2": "CClef",
    "c3": "CClef",
    "c4": "CClef",
    "cb2": "CClefChange",
    "cb3": "CClefChange",
    "cb4": "CClefChange",
    "f3": "FClef",
    "f4": "FClef",
    "f5": "FClef",
    "fb3": "FClefChange",
    "fb4": "FClefChange",
}

# Logical neume name → Gregorio glyph name (basic set; names from gregorio squarize).
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
        painter.drawText(
            dest_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
            chr(codepoint),
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
    ) -> bool:
        """
        Draw the neume glyph for neume_name into dest_rect.
        Returns True if drawn, False if fallback should be used.
        """
        if self._family is None or not self._name_to_unicode:
            return False
        key = (neume_name or "punctum").strip().lower()
        glyph_name = NEUME_NAME_TO_GLYPH.get(key)
        if glyph_name is None:
            return False
        codepoint = self._name_to_unicode.get(glyph_name)
        if codepoint is None:
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
