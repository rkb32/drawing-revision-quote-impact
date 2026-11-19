"""One-page summary PDF. Uses the latest synthetic run only. No accuracy claims."""
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

s = json.load(open("out_run/summary.json", encoding="utf-8"))
ss = getSampleStyleSheet()
H = ParagraphStyle("H", parent=ss["Heading2"], spaceBefore=8, spaceAfter=4, fontSize=11)
B = ParagraphStyle("B", parent=ss["BodyText"], fontSize=9, leading=12)
T = ParagraphStyle("T", parent=ss["Title"], fontSize=15, spaceAfter=2)

story = [
    Paragraph("Drawing Revision Quote Impact: one-page summary", T),
    Paragraph("Prototype. Tested on synthetic sheets only. No accuracy claim is made.", B),
    Paragraph("What it does", H),
    Paragraph("Takes the old and new drawing, the BOM and the vendor quote sheet. It reads about a dozen fields "
              "from text, from OCR'd scans and from rotated sheets. It cross-checks the revision block against "
              "what it found, and lists where each change sits on the sheet. A field it cannot read is flagged "
              "UNCHECKED, never treated as 'no change'. Engineering time and material cost are not priced.", B),
    Paragraph("Example run (synthetic pair, part 1234-STD, qty 24)", H),
]

rows = [["Change", "Rev A", "Rev B", "Action", "Priced?"],
        ["Stud length", "4.00 in", "5.00 in", "Requote", "Yes"],
        ["Material", "A193 B7", "A320 L7", "Requote (certs, nuts)", "Yes, same stud line"],
        ["Hole count", "8", "12", "Requote (stud qty)", "Yes, same stud line"]]
t = Table(rows, colWidths=[1.2 * inch, 1.0 * inch, 1.0 * inch, 2.0 * inch, 1.6 * inch])
t.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
]))
story += [t, Spacer(1, 6)]
ex = s["priced_exposure_by_vendor_usd"]
story.append(Paragraph(
    "Priced exposure, one vendor at a time (vendors are not added together): "
    + ", ".join(f"{v} ${a:.2f}" for v, a in ex.items())
    + f". Range ${s['priced_exposure_range_usd'][0]:.2f} to ${s['priced_exposure_range_usd'][1]:.2f}.", B))

story += [
    Paragraph("Why the rules say what they say (domain notes)", H),
    Paragraph("<b>Material A193 B7 to A320 L7:</b> L7 is for low-temperature service with impact testing. The change "
              "needs new mill certs and test results, and can change the nut spec. Price and lead time both move. "
              "Treated as Requote, not as a note. <b>Hole count:</b> a new bolt circle changes stud quantity "
              "(holes x joints) and fit. <b>Stud length:</b> a length change can also mean a different gasket or "
              "spacer stack, which this tool does not yet check.", B),
    Paragraph("What it cannot do yet", H),
    Paragraph("Real customer drawings are untested. GD&amp;T text labels and common symbols are parsed on one synthetic "
              "symbol sheet. Real GD&amp;T frames are untested. Scanned, multi-sheet and tolerance-block layouts are "
              "only partly covered. The alignment and OCR steps are untested on real scans. Locations are given for "
              "text PDFs, not for scans.", B),
    Paragraph("How accuracy would be measured", H),
    Paragraph("Take 10 or more real revision pairs with known changes. Count which changes the tool finds "
              "(recall) and which it flags wrongly (false alarms), per cost-driving field. No number exists yet.", B),
]

SimpleDocTemplate("one_pager.pdf", pagesize=letter,
                  leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                  topMargin=0.6 * inch, bottomMargin=0.6 * inch).build(story)
print("wrote one_pager.pdf")
