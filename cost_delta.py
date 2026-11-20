"""Cost delta for stud length changes: extra steel weight x material price.

Material cost only. No vendor markup, machining, or labor. Prices come from prices.csv;
the shipped placeholder row is NOT a current price (see its source column).
Rules: anything that cannot be read is reported as unpriced, never as zero.
"""
import csv
import math
import re

DENSITY_LB_IN3 = 0.2836  # carbon/alloy steel, handbook value


def parse_inches(s):
    """'5.00 in', '5', '1-1/8', '1 1/8', '1/2"' -> float inches, or None."""
    if not s:
        return None
    t = s.lower().replace('"', "").replace("inches", "").replace("inch", "").replace("in", "").strip()
    m = re.fullmatch(r"(?:(\d+)\s*[- ]\s*)?(\d+)\s*/\s*(\d+)", t)
    if m:
        den = int(m.group(3))
        if den == 0:
            return None
        return int(m.group(1) or 0) + int(m.group(2)) / den
    if re.fullmatch(r"\d+(?:\.\d+)?", t):
        return float(t)
    return None


def load_prices(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def price_range(prices, material):
    """A specific material row wins over the '*' fallback, whatever the file order."""
    m = " ".join((material or "").split()).lower()
    specific = [r for r in prices if r["material"].strip().lower() not in ("", "*")]
    fallback = [r for r in prices if r["material"].strip() == "*"]
    for r in [r for r in specific if " ".join(r["material"].split()).lower() == m] + fallback:
        try:
            return float(r["usd_per_lb_low"]), float(r["usd_per_lb_high"]), r["source"]
        except (TypeError, ValueError):
            return None
    return None


def stud_length_delta(change, bom_qty, diameter_text, prices, material):
    """Material cost change for a stud length change, across the BOM quantity."""
    old_in, new_in = parse_inches(change["old"]), parse_inches(change["new"])
    if old_in is None or new_in is None:
        return {"status": "unpriced: stud length not read as inches"}
    d = parse_inches(diameter_text)
    if d is None:
        return {"status": "unpriced: stud diameter not read"}
    if d <= 0:
        return {"status": "unpriced: stud diameter is zero"}
    if not bom_qty or bom_qty <= 0:
        return {"status": "unpriced: part not in BOM or qty is zero"}
    pr = price_range(prices, material)
    if pr is None:
        return {"status": "unpriced: no price row for this material"}
    lo, hi, source = pr
    lb_per_in = DENSITY_LB_IN3 * math.pi / 4 * d * d
    delta_lb = (new_in - old_in) * lb_per_in * bom_qty
    return {
        "status": "priced (material only, no vendor markup)",
        "delta_lb": round(delta_lb, 2),
        "delta_usd_low": round(delta_lb * lo, 2),
        "delta_usd_high": round(delta_lb * hi, 2),
        "price_source": source,
    }
