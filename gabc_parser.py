#!/usr/bin/env python3
"""
Simple GABC (Gregorian chant notation) parser.

GABC files have:
  1. A header: lines of "key: value;" (only 'name' is required).
  2. A body after "%%": (clef) and syllable(notes) tokens, with bars like (,) (;) (:) (::).

This module parses .gabc text into a simple in-memory structure and can
serialize it back to GABC text. No GUI; intended for CLI or reuse elsewhere.

Use from another module:

    from gabc_parser import GabcParser, GabcDocument, Clef, Bar, Syllable

    parser = GabcParser()
    doc = parser.parse_file("score.gabc")
    doc = parser.parse("name: X; %% (c3) A(g)")
    text = parser.serialize(doc)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import List, Union


# ---------------------------------------------------------------------------
# Data structures (minimal document model)
# ---------------------------------------------------------------------------

@dataclass
class Clef:
    """Clef at the start of the score or after a clef change. Value is e.g. 'c3', 'f4', 'cb2'."""
    value: str


@dataclass
class Bar:
    """Bar / divisio: , ; : :: ;1 ;2 etc."""
    value: str


@dataclass
class Syllable:
    """One syllable of text with its notes. Text can be empty (e.g. for a bar that has no text)."""
    text: str
    notes: str


# One body element: clef, bar, or syllable.
BodyElement = Union[Clef, Bar, Syllable]


@dataclass
class GabcDocument:
    """Parsed GABC: headers (key -> value) and a list of body elements."""
    headers: dict[str, str] = field(default_factory=dict)
    body: List[BodyElement] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser class (use this from main or other modules)
# ---------------------------------------------------------------------------

class GabcParser:
    """
    Parses GABC text or files into GabcDocument and serializes back to GABC text.
    Use from another module like:

        from gabc_parser import GabcParser, GabcDocument

        parser = GabcParser()
        doc = parser.parse_file("score.gabc")
        text = parser.serialize(doc)
    """

    # Clef pattern: (c3), (f4), (cb2) — letter c or f, optional b, digit(s).
    _CLEF_RE = re.compile(r"^[cf](?:b)?\d+$")

    def parse(self, text: str) -> GabcDocument:
        """Parse full GABC file text into a GabcDocument."""
        parts = text.split("%%", 1)
        header_text = parts[0].strip()
        body_text = parts[1].strip() if len(parts) > 1 else ""

        headers = self._parse_header(header_text)
        body = self._parse_body(body_text) if body_text else []

        return GabcDocument(headers=headers, body=body)

    def parse_file(self, path: str) -> GabcDocument:
        """Parse a .gabc file from disk."""
        with open(path, encoding="utf-8") as f:
            return self.parse(f.read())

    def serialize(self, doc: GabcDocument) -> str:
        """Turn a GabcDocument back into GABC text."""
        out = self._serialize_header(doc.headers)
        out += "\n%%\n"
        parts = [self._serialize_element(el) for el in doc.body]
        out += " ".join(parts)
        return out

    # -----------------------------------------------------------------------
    # Header parsing (private helpers)
    # -----------------------------------------------------------------------

    def _parse_header(self, header_text: str) -> dict[str, str]:
        """
        Parse the header section (everything before %%).
        Each line is "key: value;" or "key: value;;" for multi-line (value continues until ;;).
        """
        result: dict[str, str] = {}
        full = header_text.strip()
        if not full:
            return result

        current_key: str | None = None
        current_parts: list[str] = []

        for line in full.splitlines():
            line = line.rstrip()
            if ";;" in line:
                part, _ = line.split(";;", 1)
                part = part.strip()
                if current_key is not None:
                    current_parts.append(part)
                    result[current_key] = " ".join(current_parts).strip()
                    current_key = None
                    current_parts = []
                elif ":" in part:
                    key, val = part.split(":", 1)
                    key, val = key.strip(), val.strip().rstrip(";").strip()
                    if key:
                        result[key] = val
                continue
            if ";" in line and current_key is None:
                key, rest = line.split(":", 1)
                key = key.strip()
                rest = rest.strip().rstrip(";").strip()
                if key:
                    result[key] = rest
                continue
            if ":" in line and current_key is None:
                key, rest = line.split(":", 1)
                key = key.strip()
                rest = rest.strip().rstrip(";").strip()
                if key:
                    current_key = key
                    current_parts = [rest] if rest else []
                continue
            if current_key is not None:
                current_parts.append(line.strip())
                continue
            if line.strip() and ":" in line:
                k, v = line.split(":", 1)
                if k.strip():
                    result[k.strip()] = v.strip().rstrip(";").strip()

        if current_key is not None:
            result[current_key] = " ".join(current_parts).strip()

        return result

    def _read_balanced_parens(self, s: str, start: int) -> tuple[str, int]:
        """Read from s[start] (must be '(') to matching ')'; return (content, index past ')')."""
        if start >= len(s) or s[start] != "(":
            return "", start
        depth = 1
        i = start + 1
        content_start = i
        while i < len(s) and depth > 0:
            if s[i] == "(":
                depth += 1
            elif s[i] == ")":
                depth -= 1
            i += 1
        content = s[content_start : i - 1] if depth == 0 else s[content_start:i]
        return content, i

    def _is_clef(self, content: str) -> bool:
        """True if content is a clef spec (e.g. c3, f4, cb2)."""
        return bool(self._CLEF_RE.match(content.strip()))

    def _is_bar(self, content: str) -> bool:
        """True if content is a bar (e.g. , ; : :: ;1)."""
        c = content.strip()
        if not c:
            return False
        if c in (",", ";", ":", "::"):
            return True
        if c.startswith(";") and len(c) > 1 and c[1:].isdigit():
            return True
        return False

    def _parse_body(self, body_text: str) -> List[BodyElement]:
        """Parse body after %%. Tokens: (clef), (bar), or text(notes)."""
        body_text = body_text.strip()
        elements: List[BodyElement] = []
        i = 0
        token_start = 0

        while i < len(body_text):
            while i < len(body_text) and body_text[i] in " \t\n\r":
                i += 1
            if i >= len(body_text):
                break
            token_start = i

            if body_text[i] == "(":
                # Standalone (clef) or (bar), or notes for syllable we haven't seen yet
                content, end = self._read_balanced_parens(body_text, i)
                syllable_text = body_text[token_start:i].strip()

                if self._is_clef(content):
                    if syllable_text:
                        elements.append(Syllable(syllable_text, ""))
                    elements.append(Clef(content))
                elif self._is_bar(content):
                    if syllable_text:
                        elements.append(Syllable(syllable_text, ""))
                    elements.append(Bar(content))
                else:
                    elements.append(Syllable(syllable_text, content))
                i = end
                token_start = end
                continue

            # Syllable text before '(': advance until we find the opening paren
            while i < len(body_text) and body_text[i] != "(":
                i += 1
            if i >= len(body_text):
                trailing = body_text[token_start:].strip()
                if trailing:
                    elements.append(Syllable(trailing, ""))
                break

            # We're at '('; process it in this iteration so token_start still points at syllable text
            content, end = self._read_balanced_parens(body_text, i)
            syllable_text = body_text[token_start:i].strip()

            if self._is_clef(content):
                if syllable_text:
                    elements.append(Syllable(syllable_text, ""))
                elements.append(Clef(content))
            elif self._is_bar(content):
                if syllable_text:
                    elements.append(Syllable(syllable_text, ""))
                elements.append(Bar(content))
            else:
                elements.append(Syllable(syllable_text, content))
            i = end
            token_start = end

        return elements

    def _serialize_header(self, headers: dict[str, str]) -> str:
        lines = [f"{k}: {v};" for k, v in headers.items()]
        return "\n".join(lines)

    def _serialize_element(self, el: BodyElement) -> str:
        if isinstance(el, Clef):
            return f"({el.value})"
        if isinstance(el, Bar):
            return f"({el.value})"
        if isinstance(el, Syllable):
            if el.notes:
                return f"{el.text}({el.notes})"
            return el.text
        return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python gabc_parser.py <file.gabc>", file=sys.stderr)
        print("  Parses the file and prints a short summary (headers + body element count).", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    parser = GabcParser()
    try:
        doc = parser.parse_file(path)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing {path}: {e}", file=sys.stderr)
        sys.exit(1)

    print("Headers:", list(doc.headers.keys()))
    for k, v in doc.headers.items():
        print(f"  {k}: {v!r}")
    print(f"Body: {len(doc.body)} elements")
    for i, el in enumerate(doc.body[:20]):
        if isinstance(el, Clef):
            print(f"  [{i}] Clef({el.value!r})")
        elif isinstance(el, Bar):
            print(f"  [{i}] Bar({el.value!r})")
        else:
            print(f"  [{i}] Syllable({el.text!r}, {el.notes!r})")
    if len(doc.body) > 20:
        print(f"  ... and {len(doc.body) - 20} more")

    # Round-trip check: serialize and re-parse
    try:
        back = parser.serialize(doc)
        doc2 = parser.parse(back)
        if len(doc2.body) != len(doc.body):
            print("(Round-trip warning: body length changed)", file=sys.stderr)
        else:
            print("(Round-trip parse OK)")
    except Exception as e:
        print(f"(Round-trip failed: {e})", file=sys.stderr)


if __name__ == "__main__":
    _main()
