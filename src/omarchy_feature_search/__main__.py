"""Entry point: ``python -m omarchy_feature_search`` or the console script."""

from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from omarchy_feature_search.app import MainWindow
    from omarchy_feature_search.theme import load_theme

    app = QApplication(sys.argv)
    app.setApplicationName("Omarchy Feature Search")
    theme = load_theme()
    win = MainWindow(theme)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
