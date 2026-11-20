"""A text change outside the field rules must raise the uncovered-text warning, never pass silently.
Synthetic PDFs only; writes to a temp folder."""
import csv
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import pymupdf  # noqa: E402
import impact  # noqa: E402


def _pdf(path, lines):
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    for i, line in enumerate(lines):
        page.insert_text((50, 80 + i * 20), line, fontsize=11, fontname="helv")
    doc.save(path)
    doc.close()


def _csv(path, header):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(header)


class UncoveredTextWarning(unittest.TestCase):
    def test_text_outside_rules_raises_warning(self):
        tmp = tempfile.mkdtemp(prefix="warn_")
        a, b = os.path.join(tmp, "a.pdf"), os.path.join(tmp, "b.pdf")
        _pdf(a, ["STUD ASSEMBLY 1234-STD", "Culvert note: bedding class A"])
        _pdf(b, ["STUD ASSEMBLY 1234-STD", "Culvert note: bedding class B"])
        bom, quotes = os.path.join(tmp, "bom.csv"), os.path.join(tmp, "q.csv")
        _csv(bom, ["line", "description", "qty", "part_no", "uom"])
        _csv(quotes, ["vendor", "line", "part_no", "unit_price_usd", "valid_until"])
        s = impact.run(a, b, bom, quotes, "1234-STD", os.path.join(tmp, "out"))
        self.assertIsNotNone(s["uncovered_text_warning"])
        self.assertIn("review the sheets", s["uncovered_text_warning"])


if __name__ == "__main__":
    unittest.main()
