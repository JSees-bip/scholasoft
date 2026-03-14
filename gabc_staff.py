"""
Maps parsed GABC (GabcDocument) into a displayable format for the UI.
One class, GabcStaff, with all related logic; main.py imports and uses it.
Outputs neume groups (shape + pitches) so the UI can draw with the Neumes class.
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
    clef_pitch: int = 2  # Pitch index (0–12) for clef letter; e.g. c3 -> 2. UI uses for staff alignment.
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
                neumes = [
                    {"shape": shape, "pitches": pits}
                    for pits, shape in self._notes_to_neume_groups(el.notes)
                ]
                elements.append({
                    "type": "syllable",
                    "text": el.text,
                    "notes": el.notes,
                    "pitches": pitches,
                    "neumes": neumes,
                })
            # else skip unknown body element

        clef_pitch = self._clef_pitch_from_value(clef_value)
        return StaffDisplay(
            staff_line_count=staff_line_count,
            clef_value=clef_value,
            clef_pitch=clef_pitch,
            elements=elements,
        )

    def _clef_pitch_from_value(self, clef_value: str) -> int:
        """Pitch index (0–12) for the clef letter; e.g. c3 -> 2. Used for staff line alignment."""
        if not clef_value:
            return 2
        letter = clef_value[0].lower()
        if letter in _PITCH_LETTERS:
            return _PITCH_LETTERS.index(letter)
        return 2

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

    def _notes_to_neume_groups(self, notes: str) -> list[tuple[list[int], str]]:
        """
        Split GABC notes into neume groups (each group: list of pitch indices, shape name).
        GABC: "/" separates neumes; "/0" and "/!" are part of the same neume.
        Returns list of (pitches, shape) for use with the Neumes class.
        """
        if not notes or not notes.strip():
            return []

        # Split into group strings: on "/" but not on "/0" or "/!"
        groups: list[str] = []
        i = 0
        current: list[str] = []
        while i < len(notes):
            if notes[i] == "/" and i + 1 < len(notes) and notes[i + 1] in "0!":
                current.append(notes[i : i + 2])
                i += 2
                continue
            if notes[i] == "/":
                groups.append("".join(current))
                current = []
                i += 1
                continue
            current.append(notes[i])
            i += 1
        if current:
            groups.append("".join(current))

        out: list[tuple[list[int], str]] = []
        for g in groups:
            pitches = [_PITCH_LETTERS.index(c) for c in g.lower() if c in _PITCH_LETTERS]
            if not pitches:
                continue
            shape = self._infer_neume_shape(g, pitches)
            out.append((pitches, shape))
        return out

    def _infer_neume_shape(self, group_str: str, pitches: list[int]) -> str:
        """Infer logical neume shape from pitch contour and GABC modifiers."""
        n = len(pitches)
        if n == 1:
            if "v" in group_str.lower():
                return "virga"
            if "s" in group_str.lower():
                return "bistropha"
            if "w" in group_str.lower():
                return "quilisma"
            if "o" in group_str.lower():
                return "punctum"
            return "punctum"
        if n == 2:
            a, b = pitches[0], pitches[1]
            if a < b:
                return "podatus"
            if a > b:
                return "clivis"
            return "bistropha"
        if n == 3:
            a, b, c = pitches[0], pitches[1], pitches[2]
            if a < b and b < c:
                return "scandicus"
            if a > b and b > c:
                return "climacus"
            if a < b and b > c:
                return "torculus"
            if a > b and b < c:
                return "porrectus"
            if a == b == c:
                return "tristropha"
            if a < b:
                return "scandicus"
            return "climacus"
        if n >= 3:
            a, b, c = pitches[0], pitches[1], pitches[2]
            if a < b and b < c:
                return "scandicus"
            if a > b and b > c:
                return "climacus"
            if a < b and b > c:
                return "torculus"
            if a > b and b < c:
                return "porrectus"
        return "punctum"
