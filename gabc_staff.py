"""
Maps parsed GABC (GabcDocument) into a displayable format for the UI.
One class, GabcStaff, with all related logic; main.py imports and uses it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gabc_parser import GabcDocument, Clef, Bar, Syllable


# GABC pitch letters a–m map to staff positions 0–12 (a=0, m=12).
_PITCH_LETTERS = "abcdefghijklm"


@dataclass
class StaffDisplay:
    """Result of building display from a GabcDocument. UI uses this to draw the staff."""
    staff_line_count: int = 4
    clef_value: str = "c3"
    elements: list[dict[str, Any]] = field(default_factory=list)


class GabcStaff:
    """
    Translates a parsed GabcDocument into a StaffDisplay: staff layout plus
    a list of drawable elements (clef, bar, syllable with text and pitch indices).
    """

    def build_display(self, doc: GabcDocument) -> StaffDisplay:
        """
        Convert a GabcDocument into a StaffDisplay that the UI can plot.
        Reads staff-lines and clef from doc; walks body and builds elements.
        """
        staff_line_count = self._staff_line_count_from_headers(doc.headers)
        clef_value = "c3"
        elements: list[dict[str, Any]] = []

        for el in doc.body:
            if isinstance(el, Clef):
                clef_value = el.value
                elements.append({"type": "clef", "value": el.value})
            elif isinstance(el, Bar):
                elements.append({"type": "bar", "value": el.value})
            elif isinstance(el, Syllable):
                pitches = self._notes_to_pitch_indices(el.notes)
                elements.append({
                    "type": "syllable",
                    "text": el.text,
                    "notes": el.notes,
                    "pitches": pitches,
                })
            # else skip unknown body element

        return StaffDisplay(
            staff_line_count=staff_line_count,
            clef_value=clef_value,
            elements=elements,
        )

    def _staff_line_count_from_headers(self, headers: dict[str, str]) -> int:
        """Default 4 lines; respect staff-lines header if present."""
        raw = headers.get("staff-lines", "4").strip()
        try:
            n = int(raw)
            return max(2, min(5, n))
        except ValueError:
            return 4

    def _notes_to_pitch_indices(self, notes: str) -> list[int]:
        """
        Extract pitch indices (0–12) from a notes string (e.g. 'eh/hi' -> [4,7,7,8]).
        Only letters a–m (case-insensitive) count; / and other chars are skipped
        for spacing but we still output one position per note character.
        """
        result: list[int] = []
        for c in notes:
            lower = c.lower()
            if lower in _PITCH_LETTERS:
                result.append(_PITCH_LETTERS.index(lower))
        return result
