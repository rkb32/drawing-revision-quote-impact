"""Drawing revision -> quote impact.

Rules: a field that cannot be read is never treated as "no change".
Every change row ends with a price or an explicit "unpriced: <reason>".
"""
import csv
import json
import os
import re
from dataclasses import dataclass, field

import cv2
import numpy as np
import pdfplumber
import pymupdf
from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = json.load(open(os.path.join(HERE, "rules.json"), encoding="utf-8"))


@dataclass
class Extract:
    values: dict = field(default_factory=dict)   # field -> str | None
    status: dict = field(default_factory=dict)   # field -> FOUND | NOT FOUND | NO TEXT LAYER


_OCR = None


def _ocr_text(pdf_path):
    """Offline OCR (rapidocr) for pages with no text layer. Returns (text, used_ocr)."""
    global _OCR
    from rapidocr_onnxruntime import RapidOCR
    if _OCR is None:
        _OCR = RapidOCR()
    doc = pymupdf.open(pdf_path)
    lines = []
    for pg in doc:
        pix = pg.get_pixmap(dpi=300)
        png = os.path.join(os.path.dirname(os.path.abspath(pdf_path)), "_ocr_tmp.png")
        pix.save(png)
        res, _ = _OCR(png)
        os.remove(png)
        items = sorted(((r[0][0][1], r[0][0][0], r[1]) for r in (res or [])), key=lambda t: (round(t[0] / 12), t[1]))
        row_y, row = None, []
        for y, x, txt in items:
            if row_y is None or abs(y - row_y) > 12:
                if row:
                    lines.append(" ".join(row))
                row, row_y = [txt], y
            else:
                row.append(txt)
        if row:
            lines.append(" ".join(row))
    return "\n".join(lines), True


def page_text(pdf_path):
    # PyMuPDF reads rotated pages in reading order; pdfplumber returns rotated text reversed.
    doc = pymupdf.open(pdf_path)
    return "\n".join(pg.get_text() for pg in doc), False


_DIM = re.compile(r"\d+\.\d+|\d+/\d+|\d+[\"']")
_CORE = ("stud_len", "material", "holes", "qty")


def extract(pdf_path):
    text, _ = page_text(pdf_path)
    out = _read(text, "")
    # OCR only when the text layer is thin AND the core fields were not found. Digital sheets
    # skip OCR entirely; a sheet whose dimensions are outlines gets OCR and is marked "(OCR)".
    thin = len(_DIM.findall(text)) < 10
    missing = any(not out.status.get(f, "").startswith("FOUND") for f in _CORE)
    if thin and missing:
        ocr, _ = _ocr_text(pdf_path)
        out = _read(text + "\n" + ocr, " (OCR)")
    return out


def _read(text, suffix):
    out = Extract()
    if not text.strip():
        for name in RULES["fields"]:
            out.values[name] = None
            out.status[name] = "NO TEXT (OCR EMPTY)"
        return out
    for name, spec in RULES["fields"].items():
        if spec.get("findall"):
            hits = sorted(" ".join(m.group(0).split()).lower() for m in re.finditer(spec["pattern"], text, flags=re.IGNORECASE))
            out.values[name] = ", ".join(hits) if hits else "none"
            out.status[name] = "FOUND" + suffix
            continue
        m = re.search(spec["pattern"], text, flags=re.IGNORECASE)
        if m:
            out.values[name] = " ".join(next((g for g in m.groups() if g), m.group(0)).split()).lower()
            out.status[name] = "FOUND" + suffix
        elif spec.get("absent_ok"):
            out.values[name] = "none"
            out.status[name] = "FOUND" + suffix
        else:
            out.values[name] = None
            out.status[name] = "NOT FOUND" + suffix
    return out


def locate(pdf_path, value):
    """Page and position (pt) of the first word of a value on the sheet, or None."""
    if not value or value == "none":
        return None
    first = value.split(",")[0].split()[0].lower().strip(",.")
    doc = pymupdf.open(pdf_path)
    for i, pg in enumerate(doc):
        for w in pg.get_text("words"):
            if w[4].lower().strip(",.") == first:
                return {"page": i + 1, "x": round(w[0]), "y": round(w[1])}
    return None


REV_ROW = re.compile(r"^\s*([A-Z])\s+(?:ECN-\d+\s+)?(\d{4}-\d{2}-\d{2})\s+(.+)$", re.MULTILINE)


def revision_block(pdf_path):
    """{rev_letter: description} from the revision block text."""
    rows = {}
    for m in REV_ROW.finditer(page_text(pdf_path)[0]):
        rows[m.group(1)] = m.group(3).strip()
    return rows


def cross_check(changes, a_path, b_path):
    """Compare revision-block claims in rev B (new rows) with the diffs found.
    Returns list of mismatches: 'BLOCK CLAIM NOT FOUND' or 'NOT IN REVISION BLOCK'."""
    ra, rb = revision_block(a_path), revision_block(b_path)
    new_desc = " ".join(desc for rev, desc in rb.items() if rev not in ra)
    claimed = set()
    for word, field_name in RULES["block_keywords"].items():
        if re.search(word, new_desc, flags=re.IGNORECASE):
            claimed.add(field_name)
    found = {c["field"] for c in changes}
    out = []
    for f in sorted(claimed - found):
        out.append({"type": "BLOCK CLAIM NOT FOUND IN DRAWING", "field": f, "block_text": new_desc})
    for f in sorted(found - claimed):
        out.append({"type": "NOT IN REVISION BLOCK", "field": f, "block_text": new_desc})
    return out


def latest_rev(pdf_path):
    """Highest revision letter in the revision block, or None if no block was read."""
    revs = revision_block(pdf_path)
    return max(revs) if revs else None


def rev_guard(quote_rows, part_no, new_pdf):
    """Flags quote lines that are not on the revision of the new drawing.
    A quote with no 'rev' column is flagged, never passed: we cannot confirm the revision."""
    current = latest_rev(new_pdf)
    out = []
    for q in quote_rows:
        if q.get("part_no") != part_no:
            continue
        vendor = q.get("vendor", "-")
        if current is None:
            out.append({"vendor": vendor, "status": "NO REV BLOCK READ",
                        "detail": "cannot tell which revision the new drawing is"})
        elif not (q.get("rev") or "").strip():
            out.append({"vendor": vendor, "status": "QUOTE HAS NO REV",
                        "detail": f"add a rev column to the quote; new drawing is rev {current}"})
        elif q["rev"].strip().upper() != current:
            out.append({"vendor": vendor, "status": "QUOTE ON OLD REV",
                        "detail": f"quote rev {q['rev'].strip()}, new drawing rev {current}"})
    return out


def write_overlay(pa, pb, out_png, dpi=100):
    """Colour overlay after alignment: old-only ink red, new-only ink blue, shared ink black."""
    def render(path):
        doc = pymupdf.open(path)
        pix = doc[0].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        return np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w).copy()

    a, b = render(pa), render(pb)
    h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    a, b = a[:h, :w], b[:h, :w]
    (dx, dy), _ = cv2.phaseCorrelate(np.float32(a), np.float32(b))
    M = np.float32([[1, 0, -round(dx)], [0, 1, -round(dy)]])
    b = cv2.warpAffine(b, M, (w, h), borderValue=255)
    ink_a, ink_b = a < 128, b < 128
    img = np.full((h, w, 3), 255, np.uint8)
    img[ink_a & ink_b] = (0, 0, 0)
    img[ink_a & ~ink_b] = (0, 0, 255)   # BGR red: only on old
    img[ink_b & ~ink_a] = (255, 0, 0)   # BGR blue: only on new
    cv2.imwrite(out_png, img)
    return out_png


def diff(a: Extract, b: Extract):
    """Return (changes, unchecked). unchecked = fields we could not read on one side."""
    changes, unchecked = [], []
    for name, spec in RULES["fields"].items():
        sa, sb = a.status[name], b.status[name]
        if not (sa.startswith("FOUND") and sb.startswith("FOUND")):
            unchecked.append({"field": name, "rev_A": sa, "rev_B": sb})
            continue
        if a.values[name] != b.values[name]:  # values are normalized (lowercase, single spaces)
            changes.append({
                "field": name,
                "old": a.values[name],
                "new": b.values[name],
                "action": spec["action"],
                "reason": spec["reason"],
            })
    return changes, unchecked


def load_csv(path):
    """Accepts CSV or XLSX (first sheet, first row = header)."""
    if path.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True, data_only=True).worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        header = [str(h).strip() for h in rows[0]]
        return [{h: ("" if v is None else str(v)) for h, v in zip(header, r)} for r in rows[1:] if any(r)]
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def price_rows(changes, bom, quotes, part_no):
    """One row per change x vendor. Priced only for priced_actions with a quote on file."""
    bom_line = next((r for r in bom if r["part_no"] == part_no), None)
    vendor_quotes = [q for q in quotes if q["part_no"] == part_no]
    rows = []
    for ch in changes:
        if bom_line is None:
            rows.append({**ch, "vendor": "-", "unit_usd": None, "qty": None,
                         "exposure_usd": None, "status": f"unpriced: part {part_no} not in BOM"})
            continue
        if not vendor_quotes:
            rows.append({**ch, "vendor": "-", "unit_usd": None, "qty": int(bom_line["qty"]),
                         "exposure_usd": None, "status": f"unpriced: no quote for {part_no}"})
            continue
        for q in vendor_quotes:
            qty = int(bom_line["qty"])
            unit = float(q["unit_price_usd"])
            if ch["action"] in RULES["priced_actions"]:
                # Exposure is counted once per vendor per BOM line, however many changes hit it.
                first = not any(r.get("vendor") == q["vendor"] and r["exposure_usd"] is not None
                                for r in rows)
                rows.append({**ch, "vendor": q["vendor"], "unit_usd": unit, "qty": qty,
                             "exposure_usd": round(unit * qty, 2) if first else None,
                             "status": "priced" if first else "priced (counted in first change row)"})
            else:
                rows.append({**ch, "vendor": q["vendor"], "unit_usd": unit, "qty": qty,
                             "exposure_usd": None,
                             "status": f"unpriced: {ch['action'].lower()} needed"})
    return rows


def raster_regions(pa, pb, dpi=200, min_area=None, thresh=40):
    """Return (boxes_px, shift_px). Pages are aligned by phase correlation first."""
    def render(path):
        doc = pymupdf.open(path)
        pix = doc[0].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        return np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w).copy()

    a, b = render(pa), render(pb)
    if a.shape != b.shape:
        h, w = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
        a, b = a[:h, :w], b[:h, :w]
    (dx, dy), _ = cv2.phaseCorrelate(np.float32(a), np.float32(b))
    dx, dy = round(dx), round(dy)  # integer shift: no resampling blur on text edges
    M = np.float32([[1, 0, -dx], [0, 1, -dy]])
    valid = cv2.warpAffine(np.full(b.shape, 255, np.uint8), M, (b.shape[1], b.shape[0]), borderValue=0)
    b = cv2.warpAffine(b, M, (b.shape[1], b.shape[0]), borderValue=255)
    # blur before diff: sub-pixel offsets and antialiasing make 1-px text edges differ
    a = cv2.GaussianBlur(a, (5, 5), 1.5)
    b = cv2.GaussianBlur(b, (5, 5), 1.5)
    diff_img = cv2.absdiff(a, b)
    diff_img[valid == 0] = 0  # ignore the band that only exists in one sheet after the shift
    _, mask = cv2.threshold(diff_img, thresh, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    if min_area is None:
        min_area = int(dpi * dpi * 0.002)
    boxes = [tuple(int(v) for v in stats[i][:4]) for i in range(1, n) if stats[i][4] >= min_area]
    return boxes, (int(dx), int(dy))


def write_markup(pdf_in, pdf_out, boxes, dpi=200):
    doc = pymupdf.open(pdf_in)
    page = doc[0]
    s = 72 / dpi
    for x, y, w, h in boxes:
        page.draw_rect(pymupdf.Rect(x * s, y * s, (x + w) * s, (y + h) * s),
                       color=(1, 0, 0), width=1.5)
    doc.save(pdf_out)


def write_xlsx(path, rows, unchecked, total, boxes_count, shift):
    wb = Workbook()
    ws = wb.active
    ws.title = "impact"
    ws.append(["field", "old", "new", "action", "vendor", "qty", "unit_usd", "exposure_usd", "status", "reason"])
    def safe(v):
        # PDF-derived text starting with a formula character would run as a formula in Excel
        return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v
    for r in rows:
        ws.append([safe(x) for x in [r["field"], r["old"], r["new"], r["action"], r["vendor"], r["qty"],
                   r["unit_usd"], r["exposure_usd"], r["status"], r["reason"]]])
    ws.append([])
    for vendor, amt in total.items():
        ws.append([f"priced_exposure_usd ({vendor}, one vendor only)", amt])
    ws.append(["unpriced_rows", sum(1 for r in rows if r["status"].startswith("unpriced"))])
    ws.append(["UNCHECKED_fields", "; ".join(f"{u['field']} (A={u['rev_A']}, B={u['rev_B']})" for u in unchecked) or "none"])
    ws.append(["raster_boxes", boxes_count])
    ws.append(["raster_shift_px", str(shift)])
    wb.save(path)


def run(old_pdf, new_pdf, bom_csv, quotes_csv, part_no, out_dir, prices_csv=None, heat_certs_csv=None):
    os.makedirs(out_dir, exist_ok=True)
    a, b = extract(old_pdf), extract(new_pdf)
    changes, unchecked = diff(a, b)
    import cost_delta as _cd
    bom_line = next((r for r in load_csv(bom_csv) if r["part_no"] == part_no), None)
    qty = int(bom_line.get("qty", "")) if bom_line and str(bom_line.get("qty", "")).strip().isdigit() else None
    price_error = None
    try:
        prices = _cd.load_prices(prices_csv) if prices_csv else None
    except (OSError, UnicodeDecodeError, ValueError, csv.Error) as e:
        prices, price_error = None, str(e)
    cost = []
    # Every cost outcome is a row, never silent: unread, no price table, or priced.
    if "stud_len" in {u["field"] for u in unchecked}:
        cost.append({"field": "stud_len", "status": "unpriced: stud length not read on one or both sheets"})
    for ch in changes:
        if ch["field"] == "stud_len":
            if price_error:
                cost.append({"field": "stud_len", "status": "unpriced: price file unreadable (" + price_error + ")"})
                continue
            if prices is None:
                cost.append({"field": "stud_len", "status": "unpriced: no price table supplied"})
                continue
            if not (b.status.get("material") or "").startswith("FOUND") or not (a.status.get("material") or "").startswith("FOUND"):
                cost.append({"field": "stud_len", "status": "unpriced: material not read on one or both sheets"})
                continue
            both_diam = (a.status.get("diameter") or "").startswith("FOUND") and (b.status.get("diameter") or "").startswith("FOUND")
            if not both_diam or a.values.get("diameter") != b.values.get("diameter"):
                why = ("diameter changed too (weight change not computed)" if both_diam
                       else "stud diameter not read on both sheets")
                cost.append({"field": "stud_len", "status": "unpriced: " + why})
                continue
            cost.append({"field": "stud_len",
                         **_cd.stud_length_delta(ch, qty, b.values.get("diameter"), prices, b.values.get("material"))})
    import heat_check as _hc
    material_unread = "material" in {u["field"] for u in unchecked}
    heat_error = None
    if heat_certs_csv:
        try:
            heat = _hc.check(changes, _hc.load_certs(heat_certs_csv), part_no)
        except (OSError, UnicodeDecodeError, ValueError, csv.Error) as e:
            heat, heat_error = "not run: cert file unreadable (" + str(e) + ")", None
    elif any(c["field"] == "material" for c in changes):
        heat = "not run: no heat-cert file supplied"
    else:
        heat = []
    if material_unread:
        row = {"piece_mark": None, "heat_no": None, "cert_material": None, "old": None, "new": None,
               "status": "UNCHECKED", "note": "material not read on one or both sheets"}
        heat = ([] if isinstance(heat, str) else list(heat)) + [row]
    for ch in changes:
        ch["loc_old"] = locate(old_pdf, ch["old"])
        ch["loc_new"] = locate(new_pdf, ch["new"])
    rows = price_rows(changes, load_csv(bom_csv), load_csv(quotes_csv), part_no)
    # Exposure is per vendor. A buyer picks one vendor, so vendors are never summed together.
    by_vendor = {}
    for r in rows:
        if r["exposure_usd"] is not None:
            by_vendor[r["vendor"]] = round(by_vendor.get(r["vendor"], 0) + r["exposure_usd"], 2)
    total = by_vendor
    vals = list(by_vendor.values())
    vendor_range = (min(vals), max(vals)) if vals else None
    xcheck = cross_check(changes, old_pdf, new_pdf)
    boxes, shift = raster_regions(old_pdf, new_pdf)
    write_markup(new_pdf, os.path.join(out_dir, "markup.pdf"), boxes)
    write_overlay(old_pdf, new_pdf, os.path.join(out_dir, "overlay.png"))
    write_xlsx(os.path.join(out_dir, "impact.xlsx"), rows, unchecked, total, len(boxes), shift)
    import words as _words
    removed, added = _words.word_diff(old_pdf, new_pdf)
    import changeorder as _co
    import expiry as _ex
    quote_rows = load_csv(quotes_csv)
    guard = rev_guard(quote_rows, part_no, new_pdf)
    co_text = _co.build({"rows": rows, "priced_exposure_by_vendor_usd": total,
                         "changes_with_location": [{k: c[k] for k in ("field", "old", "new")} for c in changes]},
                        part_no)
    with open(os.path.join(out_dir, "change_order_draft.md"), "w", encoding="utf-8") as f:
        f.write(co_text)
    summary = {
        "expiry_flags": _ex.check(quote_rows, part_no),
        "rev_guard": guard,
        "new_rev": latest_rev(new_pdf),
        "text_words_removed": removed,
        "text_words_added": added,
        "changes": len(changes),
        "unchecked_fields": unchecked,
        "priced_exposure_by_vendor_usd": total,
        "priced_exposure_range_usd": vendor_range,
        "changes_with_location": [{k: c[k] for k in ("field", "old", "new", "loc_old", "loc_new")} for c in changes],
        "revision_block_cross_check": xcheck,
        "unpriced_rows": sum(1 for r in rows if r["status"].startswith("unpriced")),
        "raster_boxes": len(boxes),
        "raster_shift_px": shift,
        "cost_delta": cost,
        "heat_cert": heat,
        "uncovered_text_warning": (
            f"Text differs outside the field rules: {len(removed)} word(s) only on old drawing, "
            f"{len(added)} only on new. The rules do not cover these; review the sheets by hand."
            if removed or added else None),
        "rows": rows,
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    return summary
