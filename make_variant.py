"""Second synthetic layout: different title-block wording, a spec note, an ECN line.
Rev A -> Rev B changes: stud length 4->5 in, diameter 1/2->5/8, spec note B7->L7 (note only),
ECN recorded in revision block. Synthetic only."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

OUT = "samples_variant"


def draw(rev):
    os.makedirs(OUT, exist_ok=True)
    c = canvas.Canvas(f"{OUT}/variant_rev{rev}.pdf", pagesize=letter)
    h = letter[1]
    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.6 * inch, h - 0.8 * inch, "BOLT ASSY  P/N 1234-STD  (CUSTOMER FORMAT)")
    c.setFont("Helvetica", 10)
    length = "4.00 IN" if rev == "A" else "5.00 IN"
    dia = "1/2-13 UNC" if rev == "A" else "5/8-11 UNC"
    c.drawString(1.2 * inch, h - 2.2 * inch, f"Stud Length  {length}")
    c.drawString(1.2 * inch, h - 2.5 * inch, f"Thread  {dia}")
    c.drawString(1.2 * inch, h - 2.8 * inch, "Quantity  24")
    c.drawString(1.2 * inch, h - 3.1 * inch, "Hole Count  8")
    c.drawString(1.2 * inch, h - 3.4 * inch, "Material  A193 B7")
    spec = "A193 B7" if rev == "A" else "A320 L7"
    c.drawString(1.2 * inch, h - 3.9 * inch, f"GENERAL NOTE 4: STUDS PER SPEC {spec}, REV {'A' if rev == 'A' else 'B'}.")
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.6 * inch, 1.6 * inch, "REV   ECN        DATE         DESCRIPTION")
    c.setFont("Helvetica", 9)
    c.drawString(0.6 * inch, 1.4 * inch, "A     ECN-1001   2026-11-01   Initial release")
    if rev == "B":
        c.drawString(0.6 * inch, 1.2 * inch, "B     ECN-1002   2026-11-15   Length, thread, spec note changed")
    c.save()


if __name__ == "__main__":
    draw("A")
    draw("B")
    print("wrote", OUT)
