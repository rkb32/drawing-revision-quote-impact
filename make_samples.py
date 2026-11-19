"""Generate synthetic Rev A / Rev B fabrication drawings + mock BOM and quote sheet.
Synthetic data only (no downloaded files). Values mirror the pitch example."""
import csv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

OUT = "samples"

REV = {
    "A": {"stud_len": "4.00 in", "material": "A193 B7", "qty": "24", "holes": "8",
          "date": "2026-11-01"},
    "B": {"stud_len": "5.00 in", "material": "A320 L7", "qty": "24", "holes": "12",
          "date": "2026-11-15"},
}


def draw(rev, d):
    c = canvas.Canvas(f"{OUT}/drawing_rev{rev}.pdf", pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.6 * inch, h - 0.8 * inch, "STUD ASSEMBLY - PART 1234-STD")
    c.setFont("Helvetica", 10)
    c.drawString(0.6 * inch, h - 1.1 * inch, "Customer: Example Co   Drawing No: DWG-1234")
    # Body: stud with holes
    c.rect(1.5 * inch, 4 * inch, 4 * inch, 0.5 * inch)
    c.drawString(1.5 * inch, 3.7 * inch, f"Stud length: {d['stud_len']}")
    c.drawString(1.5 * inch, 3.4 * inch, f"Hole count: {d['holes']} x 0.25 in dia")
    c.drawString(1.5 * inch, 3.1 * inch, f"Quantity per assembly: {d['qty']}")
    c.drawString(1.5 * inch, 2.8 * inch, f"Material: {d['material']}")
    c.drawString(1.5 * inch, 2.5 * inch, "NOTE 1: Deburr all edges. Finish per spec.")
    # Revision block (table)
    y = 1.6 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.6 * inch, y + 0.3 * inch, "REVISION")
    c.drawString(1.6 * inch, y + 0.3 * inch, "DATE")
    c.drawString(3.0 * inch, y + 0.3 * inch, "DESCRIPTION")
    c.setFont("Helvetica", 10)
    revs = [("A", "2026-11-01", "Initial release")]
    if rev == "B":
        revs.append(("B", "2026-11-15", "Stud length, material, holes changed"))
    for i, (r, dt, desc) in enumerate(revs):
        c.drawString(0.6 * inch, y - i * 0.2 * inch, r)
        c.drawString(1.6 * inch, y - i * 0.2 * inch, dt)
        c.drawString(3.0 * inch, y - i * 0.2 * inch, desc)
    c.save()


def main():
    import os
    os.makedirs(OUT, exist_ok=True)
    for r in ("A", "B"):
        draw(r, REV[r])

    # Mock BOM: 10 lines, qty per assembly
    bom = [
        ("BOM-001", "Stud", "24", "1234-STD", "EA"),
        ("BOM-002", "Nut", "48", "NUT-500", "EA"),
        ("BOM-003", "Washer", "48", "WSH-500", "EA"),
        ("BOM-004", "Base plate", "1", "BP-200", "EA"),
        ("BOM-005", "Gasket", "2", "GSK-110", "EA"),
        ("BOM-006", "Bolt", "12", "BLT-375", "EA"),
        ("BOM-007", "Bracket", "4", "BRK-040", "EA"),
        ("BOM-008", "Spacer", "8", "SPC-020", "EA"),
        ("BOM-009", "Label", "1", "LBL-001", "EA"),
        ("BOM-010", "Packing", "1", "PKG-100", "EA"),
    ]
    with open(f"{OUT}/bom.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["line", "description", "qty", "part_no", "uom"])
        w.writerows(bom)

    # Mock quote sheet: 3 vendors x lines. Each row is vendor, line, unit price, valid_until
    vendors = ["VendorX", "VendorY", "VendorZ"]
    quotes = []
    for v_i, v in enumerate(vendors):
        for line, desc, qty, part, _ in bom:
            price = round(1.0 + 0.1 * v_i + 0.05 * int(line[-3:]), 2)
            quotes.append((v, line, part, price, "2026-12-31"))
    with open(f"{OUT}/quotes.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vendor", "line", "part_no", "unit_price_usd", "valid_until"])
        w.writerows(quotes)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
