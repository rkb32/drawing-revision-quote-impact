"""Change report CSV/PDF and per-part revision history. Synthetic data; temp files only."""
import csv
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import history  # noqa: E402
import report  # noqa: E402

ROWS = [{"field": "stud_len", "old": "4.00 in", "new": "5.00 in", "action": "Requote", "vendor": "VendorX",
         "qty": "24", "exposure_usd": 25.2, "status": "priced"}]
SUMMARY = {"changes": 1, "unpriced_rows": 0, "unchecked_fields": [], "priced_exposure_by_vendor_usd": {"VendorX": 25.2},
           "uncovered_text_warning": None, "rows": ROWS}


class ChangeReport(unittest.TestCase):
    def test_csv_has_header_and_row(self):
        tmp = tempfile.mkdtemp(prefix="rep_")
        p = os.path.join(tmp, "r.csv")
        report.write_csv(p, ROWS)
        with open(p, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["field"], "stud_len")
        self.assertEqual(rows[0]["vendor"], "VendorX")

    def test_pdf_written(self):
        tmp = tempfile.mkdtemp(prefix="rep_")
        p = os.path.join(tmp, "r.pdf")
        report.write_pdf(p, SUMMARY, "1234-STD")
        with open(p, "rb") as f:
            self.assertTrue(f.read(4) == b"%PDF")


class HostileText(unittest.TestCase):
    def test_markup_in_drawing_text_does_not_crash_the_pdf(self):
        tmp = tempfile.mkdtemp(prefix="rep_")
        s = dict(SUMMARY)
        s["unchecked_fields"] = [{"field": "<b>x", "rev_A": "<a", "rev_B": "&#xZZ;"}]
        s["uncovered_text_warning"] = "<font name='Nope'>w"
        s["rows"] = [{"field": "<b>&", "old": "<para>", "new": "a<br/>b", "action": "Requote",
                      "vendor": "<a", "qty": "1", "exposure_usd": 1, "status": "priced"}]
        p = os.path.join(tmp, "r.pdf")
        report.write_pdf(p, s, "P<a")
        with open(p, "rb") as f:
            self.assertEqual(f.read(4), b"%PDF")


class History(unittest.TestCase):
    def test_saved_runs_come_back_oldest_first(self):
        tmp = tempfile.mkdtemp(prefix="hist_")
        db = os.path.join(tmp, "h.sqlite")
        s1 = {"new_rev": "B", "changes_with_location": [{"field": "stud_len"}],
              "priced_exposure_by_vendor_usd": {"VendorX": 1.0}, "rev_guard": []}
        s2 = {"new_rev": "C", "changes_with_location": [{"field": "holes"}],
              "priced_exposure_by_vendor_usd": {}, "rev_guard": []}
        history.save(s1, "1234-STD", "A", path=db)
        history.save(s2, "1234-STD", "B", path=db)
        runs = history.history("1234-STD", path=db)
        self.assertEqual([r["new_rev"] for r in runs], ["B", "C"])
        self.assertEqual(runs[1]["changes"], ["holes"])


if __name__ == "__main__":
    unittest.main()
