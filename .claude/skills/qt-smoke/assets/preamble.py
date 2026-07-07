# Fixed preamble for every qt-smoke script: redirect the DB to a throwaway
# temp dir BEFORE init_db() (so real data is never touched), then construct
# the QApplication. Read this file and prepend it verbatim to the
# widget-specific probe code — do not retype it by hand, a skipped line
# (e.g. only setting DB_PATH and forgetting DB_DIR) breaks the isolation
# this skill exists to guarantee.

import tempfile, pathlib
import financeguru.db as db
d = pathlib.Path(tempfile.mkdtemp()) / "fg"
db.DB_DIR = d
db.DB_PATH = d / "finance.db"
db.init_db()

from PySide6.QtWidgets import QApplication
app = QApplication([])
