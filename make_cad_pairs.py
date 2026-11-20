"""Build Rev A / Rev B drawings as DXF (CAD format), then export each to PDF.
No GUI CAD tool needed: ezdxf writes the DXF, its matplotlib add-on renders the PDF.
Synthetic values only, same fields as make_samples.py. Output: samples_cad/."""
import os

import ezdxf
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

OUT = "samples_cad"

REV = {
    "A": {"stud_len": "4.00 in", "material": "A193 B7", "qty": "24", "holes": "8",
          "diameter": "1.125 in"},
    "B": {"stud_len": "5.00 in", "material": "A320 L7", "qty": "24", "holes": "12",
          "diameter": "1.125 in"},
}


def build_dxf(rev, d, path):
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_text("STUD ASSEMBLY - PART 1234-STD", dxfattribs={"height": 0.35}).set_placement((0.6, 10.2))
    msp.add_text("Customer: Example Co   Drawing No: DWG-1234", dxfattribs={"height": 0.2}).set_placement((0.6, 9.9))
    msp.add_lwpolyline([(1.5, 6.0), (5.5, 6.0), (5.5, 6.5), (1.5, 6.5), (1.5, 6.0)])
    lines = [f"Stud length: {d['stud_len']}", f"Hole count: {d['holes']} x 0.25 in dia",
             f"Quantity per assembly: {d['qty']}", f"Material: {d['material']}",
             f"Diameter: {d['diameter']}", "NOTE 1: Deburr all edges. Finish per spec."]
    for i, t in enumerate(lines):
        msp.add_text(t, dxfattribs={"height": 0.2}).set_placement((1.5, 5.6 - i * 0.3))
    y = 1.6
    msp.add_text("REVISION", dxfattribs={"height": 0.18}).set_placement((0.6, y + 0.3))
    msp.add_text("DATE", dxfattribs={"height": 0.18}).set_placement((1.6, y + 0.3))
    msp.add_text("DESCRIPTION", dxfattribs={"height": 0.18}).set_placement((3.0, y + 0.3))
    rows = [("A", "2026-11-01", "Initial release")]
    if rev == "B":
        rows.append(("B", "2026-11-15", "Stud length, material, holes changed"))
    for i, (r, dt, desc) in enumerate(rows):
        yy = y - i * 0.2
        msp.add_text(r, dxfattribs={"height": 0.18}).set_placement((0.6, yy))
        msp.add_text(dt, dxfattribs={"height": 0.18}).set_placement((1.6, yy))
        msp.add_text(desc, dxfattribs={"height": 0.18}).set_placement((3.0, yy))
    doc.saveas(path)


def dxf_to_pdf(dxf_path, pdf_path):
    """Writes TEXT and closed polylines from the DXF into a PDF with a real text layer.
    Handles only these two entity types (enough for these samples)."""
    import pymupdf
    doc = ezdxf.readfile(dxf_path)
    pdf = pymupdf.open()
    page = pdf.new_page(width=8.5 * 72, height=11 * 72)
    H = 11 * 72
    for e in doc.modelspace():
        if e.dxftype() == "TEXT":
            x, y = e.dxf.insert.x * 72, H - e.dxf.insert.y * 72
            page.insert_text((x, y), e.dxf.text, fontsize=e.dxf.height * 72, fontname="helv")
        elif e.dxftype() == "LWPOLYLINE":
            pts = [(p[0] * 72, H - p[1] * 72) for p in e.get_points()]
            shape = page.new_shape()
            shape.draw_polyline(pts)
            shape.finish(color=(0, 0, 0), width=1)
            shape.commit()
    pdf.save(pdf_path)
    pdf.close()


def main():
    os.makedirs(OUT, exist_ok=True)
    for r in ("A", "B"):
        dxf = os.path.join(OUT, f"drawing_rev{r}.dxf")
        pdf = os.path.join(OUT, f"drawing_rev{r}.pdf")
        build_dxf(r, REV[r], dxf)
        dxf_to_pdf(dxf, pdf)
        print("wrote", pdf)


if __name__ == "__main__":
    main()
