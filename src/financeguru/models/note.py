from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Note:
    body: str
    # "YYYY-MM" — the month this note is filed under. Set explicitly from
    # whichever month is selected in the Notes tab's picker when the note is
    # added, so backfilling a note into a past month works; never derived
    # from created_at.
    month_year: str
    # ISO timestamp, auto-set when the note is added. Independent of
    # month_year — a note added today can still be filed under a past month.
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    # At most one of these is set (enforced by a CHECK constraint in the DB) —
    # a note may optionally link to a single Bill or Goal, never both.
    bill_id: int | None = None
    goal_id: int | None = None
    id: int | None = None
