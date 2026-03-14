# Scholasoft

A simple tool for editing GABC (Gregorian chant notation) files: import, edit, and export sheet music. The parser and CLI are in place; a graphical editor is planned.

Full disclosure: I am using cursor AI assitance in developing this project for both research help and some code generation. 

Credit: [Gregorio project](https://github.com/gregorio-project/gregorio) for it's amazing fonts!
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

### Gregorio font (staff display)

The GUI draws clefs and neumes with the **greciliae** font from the [Gregorio project](https://github.com/gregorio-project/gregorio). The font lives in the `lib/gregorio-project` git submodule; the built `.ttf` is produced by a script and stored in `.symbols/`. If the font is missing, the app still runs and falls back to drawing clefs as text and notes as circles.

#### 1. Get the Gregorio submodule

If you cloned the repo without submodules, fetch and update them:

```bash
git submodule update --init --recursive
```

To clone the repo and submodules in one step:

```bash
git clone --recurse-submodules <repo-url>
```

#### 2. Build the greciliae font

From the **repository root**, run the build script. It reads sources from `lib/gregorio-project/fonts` (read-only) and writes `greciliae.ttf` into `.symbols/`.

```bash
python .symbols/build_greciliae_font.py
```

**Requirements:** [FontForge](https://fontforge.org/) must be installed. On Windows, if FontForge is not on your PATH, set the executable path before running the script:

```powershell
$env:FONTFORGE_EXE = "C:\Program Files (x86)\FontForgeBuilds\run_fontforge.exe"
python .symbols/build_greciliae_font.py
```

Adjust the path to match your FontForge install (e.g. `run_fontforge.exe` or `fontforge.exe`). After a successful run, the app will use `.symbols/greciliae.ttf` for clefs and neumes.

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
