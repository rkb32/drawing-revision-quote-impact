"""Shareable change report: CSV (rows) and PDF (summary + table). Synthetic-tested; no network use."""
import csv

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

COLS = ("field", "old", "new", "action", "vendor", "qty", "exposure_usd", "status")


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLS})


def write_pdf(path, s, part_no):
    st = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = [Paragraph(f"Revision impact report: part {part_no}", st["Title"]),
             Paragraph(f"Changes: {s['changes']}. Unpriced rows: {s['unpriced_rows']}. "
                       f"UNCHECKED fields: {len(s['unchecked_fields'])}.", st["Normal"]),
             Spacer(1, 8)]
    vendors = s["priced_exposure_by_vendor_usd"]
    story.append(Paragraph("Priced exposure, one vendor at a time (not added together):", st["Heading3"]))
    story += [Paragraph(f"{v}: ${a:.2f}", st["Normal"]) for v, a in vendors.items()] or [Paragraph("none", st["Normal"])]
    story.append(Spacer(1, 8))
    story.append(Paragraph("UNCHECKED (could not read on one side, NOT 'no change'):", st["Heading3"]))
    story += [Paragraph(f"{u['field']}: rev A {u['rev_A']}, rev B {u['rev_B']}", st["Normal"])
              for u in s["unchecked_fields"]] or [Paragraph("none", st["Normal"])]
    if s.get("uncovered_text_warning"):
        story += [Spacer(1, 8), Paragraph("Warning: " + s["uncovered_text_warning"], st["Normal"])]
    story += [Spacer(1, 8), Paragraph("Changes", st["Heading3"])]
    data = [list(COLS)] + [[str(r.get(k, "")) for k in COLS] for r in s["rows"]]
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeea"))]))
    story.append(t)
    doc.build(story)
