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


SCHEMA_VERSION = 1


def to_record(summary, part, old_rev=None):
    """One run as a plain dict. Used by the CLI sqlite log and by the web app's history file."""
    return {
        "part": part,
        "old_rev": old_rev if old_rev is not None else summary.get("old_rev"),
        "new_rev": summary.get("new_rev"),
        "changes": [c["field"] for c in summary["changes_with_location"]],
        "exposure_by_vendor": summary["priced_exposure_by_vendor_usd"],
        "rev_guard": summary.get("rev_guard", []),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def load_file(text, part):
    """Parse an uploaded history file. Raises ValueError on wrong schema or a different part."""
    data = json.loads(text)
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("not a revision-history file (wrong or missing schema_version)")
    if data.get("part") != part:
        raise ValueError(f"this history file is for part {data.get('part')!r}, not {part!r}")
    runs = data.get("runs")
    if not isinstance(runs, list):
        raise ValueError("history file has no runs list")
    for i, r in enumerate(runs):
        if not isinstance(r, dict):
            raise ValueError(f"run {i} is not an object")
        if not isinstance(r.get("created"), str):
            raise ValueError(f"run {i} has no created timestamp")
        if not isinstance(r.get("changes"), list) or not all(isinstance(x, str) for x in r["changes"]):
            raise ValueError(f"run {i} has a bad changes list")
        if not isinstance(r.get("exposure_by_vendor"), dict):
            raise ValueError(f"run {i} has a bad exposure_by_vendor")
    return runs


def dump_file(runs, part):
    return json.dumps({"schema_version": SCHEMA_VERSION, "part": part, "runs": runs}, indent=2)
