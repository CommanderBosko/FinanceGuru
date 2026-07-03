import sys
import traceback

from PySide6.QtWidgets import QApplication
from financeguru.db import auto_backup, init_db
from financeguru.repositories import snapshots
from financeguru.views.main_window import MainWindow


def main():
    # Daily rotating backup, deliberately BEFORE init_db(): it must capture
    # the pre-migration database so a bad migration in a new release can be
    # rolled back. A failure must never block the app from starting.
    try:
        auto_backup()
    except Exception:
        traceback.print_exc()
    init_db()
    # Record today's net-worth snapshot so trend history accrues from every
    # launch, not only on days the Stocks tab is refreshed. Launch-time hooks
    # live here, not in MainWindow, so constructing the window in tests never
    # writes snapshots. A failure must never block the app from starting.
    try:
        snapshots.capture()
    except Exception:
        traceback.print_exc()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
