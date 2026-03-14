"""
Tile-set definitions for Gregorian chant notation.
Loads symbol_set.png (neumes) and clef_set.png (clefs) from .symbols/,
defines grid layout and mappings so the UI can draw tiles when displaying music.
"""

from __future__ import annotations

import os
from typing import Tuple

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QImage, QPainter


def _symbols_dir() -> str:
    """Directory containing .symbols (sibling to this file)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".symbols")


class Clefs:
    """
    Clef tile set from clef_set.png.
    Grid and mapping from clef value (e.g. 'c3', 'f4') to (col, row).
    """

    # Tile dimensions in the sprite sheet (adjust if your image layout differs)
    TILE_WIDTH = 40
    TILE_HEIGHT = 80

    # Clef value -> (column, row) in the grid. Extend for your clef_set.png layout.
    GRID: dict[str, Tuple[int, int]] = {
        "c2": (0, 0),
        "c3": (1, 0),
        "c4": (2, 0),
        "cb2": (3, 0),
        "cb3": (4, 0),
        "cb4": (5, 0),
        "f3": (0, 1),
        "f4": (1, 1),
        "f5": (2, 1),
        "fb3": (3, 1),
        "fb4": (4, 1),
    }

    def __init__(self) -> None:
        path = os.path.join(_symbols_dir(), "clef_set.png")
        self._image: QImage | None = QImage(path) if os.path.isfile(path) else None

    @property
    def image(self) -> QImage | None:
        """Loaded clef sprite sheet, or None if file missing."""
        return self._image

    def get_source_rect(self, clef_value: str) -> QRect | None:
        """
        Source rectangle in the tile set for the given clef (e.g. 'c3', 'f4').
        Returns None if clef is unknown or image not loaded.
        """
        if self._image is None:
            return None
        key = (clef_value or "c3").strip().lower()
        if key not in self.GRID:
            key = "c3"
        col, row = self.GRID[key]
        return QRect(
            col * self.TILE_WIDTH,
            row * self.TILE_HEIGHT,
            self.TILE_WIDTH,
            self.TILE_HEIGHT,
        )

    def draw(
        self,
        painter: QPainter,
        dest_rect: QRect,
        clef_value: str,
    ) -> bool:
        """
        Draw the clef tile for clef_value into dest_rect.
        Returns True if drawn, False if fallback should be used (e.g. text).
        """
        src = self.get_source_rect(clef_value)
        if src is None or self._image is None:
            return False
        painter.drawImage(dest_rect, self._image, src)
        return True


class Neumes:
    """
    Neume tile set from symbol_set.png.
    Grid and mapping from neume name to (col, row) for the 14 standard neumes.
    """

    # Tile dimensions in the sprite sheet (adjust if your image layout differs)
    TILE_WIDTH = 48
    TILE_HEIGHT = 48

    # Neume name -> (column, row). Order matches typical symbol_set layout (e.g. 2 columns).
    GRID: dict[str, Tuple[int, int]] = {
        "punctum": (0, 0),
        "virga": (1, 0),
        "podatus": (0, 1),
        "clivis": (1, 1),
        "torculus": (0, 2),
        "porrectus": (1, 2),
        "climacus": (0, 3),
        "bistropha": (1, 3),
        "tristropha": (0, 4),
        "pressus": (1, 4),
        "quilisma": (0, 5),
        "scandicus": (1, 5),
        "salicus": (0, 6),
        "liquescent": (1, 6),
    }

    def __init__(self) -> None:
        path = os.path.join(_symbols_dir(), "symbol_set.png")
        self._image: QImage | None = QImage(path) if os.path.isfile(path) else None

    @property
    def image(self) -> QImage | None:
        """Loaded neume sprite sheet, or None if file missing."""
        return self._image

    def get_source_rect(self, neume_name: str) -> QRect | None:
        """
        Source rectangle in the tile set for the given neume (e.g. 'podatus', 'clivis').
        Returns None if neume is unknown or image not loaded.
        """
        if self._image is None:
            return None
        key = (neume_name or "punctum").strip().lower()
        if key not in self.GRID:
            return None
        col, row = self.GRID[key]
        return QRect(
            col * self.TILE_WIDTH,
            row * self.TILE_HEIGHT,
            self.TILE_WIDTH,
            self.TILE_HEIGHT,
        )

    def draw(
        self,
        painter: QPainter,
        dest_rect: QRect,
        neume_name: str,
    ) -> bool:
        """
        Draw the neume tile for neume_name into dest_rect.
        Returns True if drawn, False if fallback should be used.
        """
        src = self.get_source_rect(neume_name)
        if src is None or self._image is None:
            return False
        painter.drawImage(dest_rect, self._image, src)
        return True
