"""
Scholasoft – main entry point. Wires the UI, parser, and staff together.
"""

import sys
import time

from PyQt6.QtWidgets import QApplication

from ui import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        app.quit()


if __name__ == "__main__":
    main()
