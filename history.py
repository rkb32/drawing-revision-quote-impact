"""Per-part revision history. Opt-in only (CLI --history): the hosted and Streamlit apps never write it.
Each run saves: part, old/new revision, change fields, priced exposure per vendor, and rev-guard flags."""
import json
import os
import sqlite3
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "revisions.sqlite")


def _conn(path=DB):
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE IF NOT EXISTS revisions (
        id INTEGER PRIMARY KEY, part TEXT, old_rev TEXT, new_rev TEXT, changes TEXT,
        exposure_by_vendor TEXT, rev_guard TEXT, created TEXT)""")
    return c


def save(summary, part, old_rev, path=DB):
    """summary: dict returned by impact.run."""
    c = _conn(path)
    c.execute("INSERT INTO revisions (part, old_rev, new_rev, changes, exposure_by_vendor, rev_guard, created) "
              "VALUES (?,?,?,?,?,?,?)",
              (part, old_rev, summary.get("new_rev"),
               json.dumps([c_["field"] for c_ in summary["changes_with_location"]]),
               json.dumps(summary["priced_exposure_by_vendor_usd"]),
               json.dumps(summary.get("rev_guard", [])),
               datetime.now(timezone.utc).isoformat(timespec="seconds")))
    c.commit()
    c.close()


def history(part, path=DB):
    """All saved runs for one part, oldest first."""
    c = _conn(path)
    rows = c.execute("SELECT old_rev, new_rev, changes, exposure_by_vendor, rev_guard, created "
                     "FROM revisions WHERE part=? ORDER BY id", (part,)).fetchall()
    c.close()
    return [{"old_rev": o, "new_rev": n, "changes": json.loads(ch), "exposure_by_vendor": json.loads(ex),
             "rev_guard": json.loads(g), "created": cr} for o, n, ch, ex, g, cr in rows]
