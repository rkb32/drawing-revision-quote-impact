"""Spike: extract fields from Rev A/B PDFs, diff, map to quote lines, raster-diff regions.
Synthetic inputs from make_samples.py. Rules are hand-written; no LLM used."""
import csv, re, os
import pdfplumber, pymupdf, cv2, numpy as np
from openpyxl import Workbook

S = "samples"
FIELDS = {
    "stud_len": r"Stud length:\s*(.+)",
    "holes": r"Hole count:\s*(\d+)",
    "qty": r"Quantity per assembly:\s*(\d+)",
    "material": r"Material:\s*(.+)",
}
# Action per changed field (pitch rules)
ACTION = {"stud_len": "Requote", "material": "Revalidate",
          "qty": "Requote", "holes": "Engineering review"}


def extract(path):
    with pdfplumber.open(path) as p:
        text = p.pages[0].extract_text()
    out = {}
    for k, pat in FIELDS.items():
        m = re.search(pat, text)
        out[k] = m.group(1).strip() if m else None
    return out


def raster_regions(pa, pb, dpi=100, min_area=200):
    def render(path):
        doc = pymupdf.open(path)
        pix = doc[0].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w)
        return img
    a, b = render(pa), render(pb)
    diff = cv2.absdiff(a, b)
    _, mask = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    boxes = [tuple(int(v) for v in stats[i][:4]) for i in range(1, n)
             if stats[i][4] >= min_area]
    return boxes


def main():
    a = extract(f"{S}/drawing_revA.pdf")
    b = extract(f"{S}/drawing_revB.pdf")
    changes = [(k, a[k], b[k], ACTION[k]) for k in FIELDS if a[k] != b[k]]
    unchanged = [k for k in FIELDS if a[k] == b[k]]

    # Quote lines affected: stud part 1234-STD (BOM-001); all vendors
    quotes = list(csv.DictReader(open(f"{S}/quotes.csv")))
    bom = list(csv.DictReader(open(f"{S}/bom.csv")))
    stud = next(r for r in bom if r["part_no"] == "1234-STD")
    stud_quotes = [q for q in quotes if q["part_no"] == "1234-STD"]
    actions = {c[3] for c in changes}
    # Commercial impact for any Requote change: all 3 vendor stud quotes need reconfirm
    total_at_risk = 0.0
    rows = []
    for k, av, bv, act in changes:
        for q in stud_quotes:
            qty = int(stud["qty"])
            exposure = float(q["unit_price_usd"]) * qty
            if act == "Requote":
                total_at_risk += exposure
            rows.append([k, av, bv, act, q["vendor"], q["line"], q["part_no"],
                         q["unit_price_usd"], qty, round(exposure, 2)])

    boxes = raster_regions(f"{S}/drawing_revA.pdf", f"{S}/drawing_revB.pdf")

    os.makedirs("out", exist_ok=True)
    wb = Workbook(); ws = wb.active; ws.title = "impact"
    ws.append(["field", "rev_A", "rev_B", "action", "vendor", "bom_line",
               "part_no", "unit_price_usd", "qty", "exposure_usd"])
    for r in rows:
        ws.append(r)
    ws.append([]); ws.append(["total_requote_exposure_usd", round(total_at_risk, 2)])
    ws.append(["unchanged_fields", ", ".join(unchanged)])
    ws.append(["raster_changed_boxes_px", str(boxes)])
    wb.save("out/impact.xlsx")

    print("changes:", [(c[0], c[1], c[2], c[3]) for c in changes])
    print("unchanged:", unchanged)
    print("total requote exposure (USD):", round(total_at_risk, 2))
    print("raster boxes (px @100dpi):", boxes)


if __name__ == "__main__":
    main()
