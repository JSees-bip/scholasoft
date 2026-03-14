# Scholasoft

A simple tool for editing GABC (Gregorian chant notation) files: import, edit, and export sheet music. The parser and CLI are in place; a graphical editor is planned.

---

## Using `gabc_parser.py` (CLI)

The parser can be run from the command line to read a `.gabc` file and print a short summary.

### Command

```bash
python gabc_parser.py <file.gabc>
```

Give the path to your GABC file as the only argument.

### Example

```bash
python gabc_parser.py .testfiles/example.gabc
```

### What it does

1. Parses the file and prints all **headers** (e.g. `name`, `mode`).
2. Prints the first **20 body elements** (clef, syllables, bars) with indices.
3. If there are more than 20 elements, it prints how many are left.
4. Runs a **round-trip** (serialize back to GABC, then parse again) and reports whether it succeeded.

### If you get an error

- **File not found:** Check the path to the `.gabc` file.
- **Error parsing:** The file may not be valid GABC (e.g. missing `%%`, or malformed header/body). Fix the file and try again.

### Using the parser from Python

You can also import and use the parser in your own code:

```python
from gabc_parser import GabcParser, GabcDocument

parser = GabcParser()
doc = parser.parse_file("score.gabc")   # from file
# or
doc = parser.parse("name: X; %% (c3) A(g)")   # from string

text = parser.serialize(doc)   # back to GABC text
```
