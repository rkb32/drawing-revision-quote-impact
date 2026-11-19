"""Per-shop decision log. Estimators record requote/hold for each change. After enough
history, it suggests which rules to review. Suggestions only; nothing changes automatically."""
import json
import os
import sqlite3
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "decisions.sqlite")


def _conn(path=DB):
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY, shop TEXT, part TEXT, field TEXT, rule_action TEXT,
        decision TEXT, outcome TEXT, created TEXT)""")
    return c


def log(shop, part, field, rule_action, decision, outcome="", path=DB):
    """decision: 'requote' or 'hold'. outcome: free text, e.g. 'customer paid' or 'missed, $450'."""
    if decision not in ("requote", "hold"):
        raise ValueError("decision must be requote or hold")
    c = _conn(path)
    c.execute("INSERT INTO decisions (shop, part, field, rule_action, decision, outcome, created) "
              "VALUES (?,?,?,?,?,?,?)",
              (shop, part, field, rule_action, decision, outcome,
               datetime.now(timezone.utc).isoformat(timespec="seconds")))
    c.commit()
    c.close()


def suggestions(shop, min_n=5, path=DB):
    """Fields where the estimator almost always holds a change the rule says to requote,
    or always requotes one the rule treats as engineering review. Needs min_n decisions."""
    c = _conn(path)
    rows = c.execute("SELECT field, rule_action, decision FROM decisions WHERE shop=?", (shop,)).fetchall()
    c.close()
    out = []
    by_field = {}
    for field, rule_action, decision in rows:
        by_field.setdefault((field, rule_action), []).append(decision)
    for (field, rule_action), decs in by_field.items():
        if len(decs) < min_n:
            continue
        hold_rate = decs.count("hold") / len(decs)
        if rule_action == "Requote" and hold_rate >= 0.8:
            out.append({"field": field, "suggest": "review: estimator holds this change most of the time",
                        "n": len(decs)})
        if rule_action != "Requote" and hold_rate <= 0.2:
            out.append({"field": field, "suggest": "review: estimator requotes this change most of the time",
                        "n": len(decs)})
    return out
