# Template pattern for a guarded, idempotent one-time data rename/fixup
# migration in init_db(). Copy and adapt: swap the table/column names for
# whatever is actually being renamed, and add an UPDATE line for every
# free-text table that references the old value.
#
# Bail conditions (both required for idempotency):
#   - old not in names  -> already renamed, nothing to do
#   - new in names      -> renaming would collide with an existing row
#
# Decide deliberately whether to re-tag existing records (a *complete*
# rename) or leave them (e.g. an in-app picker rename that's deliberately
# picker-only) — state which you chose and why in a comment at the call site.

def _rename_category(conn, old, new):
    names = {r["name"] for r in conn.execute("SELECT name FROM categories")}
    if old not in names or new in names:   # already done, or would collide
        return
    conn.execute("UPDATE categories SET name=? WHERE name=?", (new, old))
    conn.execute("UPDATE bills    SET category=? WHERE category=?", (new, old))
    conn.execute("UPDATE expenses SET category=? WHERE category=?", (new, old))
