"""
Scholasoft – main entry point. Wires the UI, parser, and staff together.
All wiring and application logic lives here; ui.py and helpers stay decoupled.
"""

import sys
import time

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from gabc_parser import GabcParser, GabcDocument, Clef, Bar, Syllable
from ui import MainWindow


def format_parsed_document(doc: GabcDocument) -> str:
    """Turn a parsed GabcDocument into a readable string for the UI."""
    lines = ["=== Headers ==="]
    for key, value in doc.headers.items():
        lines.append(f"  {key}: {value!r}")
    lines.append("")
    lines.append("=== Body ===")
    for i, el in enumerate(doc.body):
        if isinstance(el, Clef):
            lines.append(f"  [{i}] Clef({el.value!r})")
        elif isinstance(el, Bar):
            lines.append(f"  [{i}] Bar({el.value!r})")
        elif isinstance(el, Syllable):
            lines.append(f"  [{i}] Syllable({el.text!r}, {el.notes!r})")
        else:
            lines.append(f"  [{i}] {el!r}")
    return "\n".join(lines)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    parser = GabcParser()

    # Pending requests from the UI; the loop processes these each iteration.
    # Signal handlers only append to this list; all real logic runs in the loop.
    pending_requests = []

    def on_file_open_requested():
        pending_requests.append("open")

    window.file_open_requested.connect(on_file_open_requested)
    window.show()

    try:
        while window.isVisible():
            app.processEvents()

            # Process any pending requests (File > Open, etc.) here in the loop.
            while pending_requests:
                req = pending_requests.pop(0)
                if req == "open":
                    docs_path = QStandardPaths.writableLocation(
                        QStandardPaths.StandardLocation.DocumentsLocation
                    ) or ""
                    path, _ = QFileDialog.getOpenFileName(
                        window,
                        "Open GABC file",
                        docs_path,
                        "GABC files (*.gabc);;All files (*)",
                    )
                    if not path:
                        continue
                    try:
                        doc = parser.parse_file(path)
                        text = f"Opened: {path}\n\n{format_parsed_document(doc)}"
                        window.set_display_text(text)
                    except FileNotFoundError:
                        QMessageBox.warning(
                            window, "Open failed", f"File not found: {path}"
                        )
                    except Exception as e:
                        QMessageBox.warning(
                            window, "Open failed", f"Could not parse file:\n{e}"
                        )

            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        app.quit()


if __name__ == "__main__":
    main()
