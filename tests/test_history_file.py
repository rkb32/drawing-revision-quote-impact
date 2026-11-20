"""Portable revision-history file: the app appends one run per upload; wrong files are rejected.
Synthetic data only."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import history  # noqa: E402

RUN = {"new_rev": "B", "old_rev": "A", "changes_with_location": [{"field": "stud_len"}],
       "priced_exposure_by_vendor_usd": {"VendorX": 25.2}, "rev_guard": []}


class HistoryFile(unittest.TestCase):
    def test_one_more_run_each_time(self):
        first = [history.to_record(RUN, "1234-STD")]
        text = history.dump_file(first, "1234-STD")
        runs = history.load_file(text, "1234-STD")
        runs.append(history.to_record({**RUN, "new_rev": "C"}, "1234-STD"))
        self.assertEqual(len(runs), len(first) + 1)
        self.assertEqual([r["new_rev"] for r in runs], ["B", "C"])

    def test_wrong_part_rejected(self):
        text = history.dump_file([history.to_record(RUN, "1234-STD")], "1234-STD")
        with self.assertRaises(ValueError):
            history.load_file(text, "OTHER-PART")

    def test_wrong_schema_rejected(self):
        with self.assertRaises(ValueError):
            history.load_file(json.dumps({"part": "1234-STD", "runs": []}), "1234-STD")
        with self.assertRaises(ValueError):
            history.load_file("not json at all", "1234-STD")


if __name__ == "__main__":
    unittest.main()
