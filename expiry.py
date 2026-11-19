"""Quote expiry watch. Flags quotes that expire before the vendor's lead time would finish,
even when the drawing has not changed. Needs valid_until (YYYY-MM-DD) in the quote sheet.
lead_time_days is optional; if missing, 0 is assumed and the check is flagged as partial."""
from datetime import date, timedelta


def check(quote_rows, part_no, today=None):
    today = today or date.today()
    out = []
    for q in quote_rows:
        if q.get("part_no") != part_no:
            continue
        try:
            valid = date.fromisoformat(q["valid_until"])
        except (KeyError, ValueError):
            out.append({"vendor": q.get("vendor", "-"), "status": "NO VALID DATE",
                        "detail": "quote has no usable valid_until date"})
            continue
        lt_raw = q.get("lead_time_days")
        lead = int(float(lt_raw)) if lt_raw not in (None, "") else 0
        finish = today + timedelta(days=lead)
        if valid < finish:
            out.append({"vendor": q.get("vendor", "-"),
                        "status": "EXPIRES BEFORE LEAD TIME ENDS" if lt_raw not in (None, "")
                        else "EXPIRES (lead time not given)",
                        "detail": f"valid until {valid}, order would finish about {finish}"})
        elif valid < today:
            out.append({"vendor": q.get("vendor", "-"), "status": "EXPIRED", "detail": f"valid until {valid}"})
    return out
