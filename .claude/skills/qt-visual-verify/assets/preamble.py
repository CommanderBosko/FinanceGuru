# Fixed preamble for every qt-visual-verify script: redirect the DB to a
# throwaway temp dir BEFORE init_db() (so real data is never touched),
# construct the QApplication, then force a readable light palette. Read this
# file and prepend it verbatim to the widget-specific driver code — do not
# retype it by hand, a skipped line (e.g. only setting DB_PATH and forgetting
# DB_DIR) breaks the isolation this skill exists to guarantee, and skipping
# the palette fix can leave screenshots solid black/illegible even though the
# widget renders correctly.

import tempfile, pathlib
import financeguru.db as db
d = pathlib.Path(tempfile.mkdtemp()) / "fg"
db.DB_DIR = d
db.DB_PATH = d / "finance.db"
db.init_db()

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
app = QApplication([])

pal = app.palette()
pal.setColor(QPalette.ColorRole.Window, QColor(250, 250, 250))
pal.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
pal.setColor(QPalette.ColorRole.WindowText, QColor(20, 20, 20))
pal.setColor(QPalette.ColorRole.Text, QColor(20, 20, 20))
app.setPalette(pal)
