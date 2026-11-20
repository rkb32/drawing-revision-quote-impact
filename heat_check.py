"""Heat-cert check on revision: flags pieces whose mill cert material no longer matches the new drawing.

Input: a heat-cert CSV you supply (one row per piece): part_no, piece_mark, heat_no, cert_material.
Rules: a material change on the drawing with no cert row is UNCHECKED, never "ok".
Only material is checked. Reading MTRs from PDFs is not built.
"""
import csv


def load_certs(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def check(changes, certs, part_no):
    """Returns one row per (piece, material change). Status: RE-CERTIFY, OK, or UNCHECKED."""
    mat = next((c for c in changes if c["field"] == "material"), None)
    if mat is None:
        return []
    old, new = (mat["old"] or "").strip().lower(), (mat["new"] or "").strip().lower()
    rows = []
    mine = [c for c in certs if c.get("part_no") == part_no]
    if not mine:
        # Material changed but no cert rows for this part: unreadable, never silent.
        return [{"piece_mark": None, "heat_no": None, "cert_material": None,
                 "old": old, "new": new, "status": "UNCHECKED"}]
    for c in mine:
        cm = (c.get("cert_material") or "").strip().lower()
        if not cm:
            status = "UNCHECKED"
        elif cm == new:
            status = "OK"
        elif cm == old:
            status = "RE-CERTIFY"
        else:
            status = "UNCHECKED"
        rows.append({"piece_mark": c.get("piece_mark"), "heat_no": c.get("heat_no"),
                     "cert_material": cm or None, "old": old, "new": new, "status": status})
    return rows
