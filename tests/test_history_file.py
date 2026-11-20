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

    def test_malformed_run_entries_rejected(self):
        bad_runs = [[{}], [1], ["x"],
                    [{"created": "t", "changes": "abc", "exposure_by_vendor": {}}],
                    [{"created": "t", "changes": ["a"], "exposure_by_vendor": []}],
                    [{"changes": [], "exposure_by_vendor": {}}]]
        for runs in bad_runs:
            text = json.dumps({"schema_version": 1, "part": "1234-STD", "runs": runs})
            with self.subTest(runs=runs), self.assertRaises(ValueError):
                history.load_file(text, "1234-STD")

    def test_nan_and_non_text_revs_rejected(self):
        base = {"created": "t", "changes": [], "exposure_by_vendor": {}}
        nan_text = json.dumps({"schema_version": 1, "part": "1234-STD", "runs": [base]}).replace(
            '"exposure_by_vendor": {}', '"exposure_by_vendor": {"V": NaN}')
        with self.assertRaises(ValueError):
            history.load_file(nan_text, "1234-STD")
        bad_rev = {**base, "old_rev": 7}
        with self.assertRaises(ValueError):
            history.load_file(json.dumps({"schema_version": 1, "part": "1234-STD", "runs": [bad_rev]}), "1234-STD")

    def test_bom_prefixed_text_loads_when_decoded_as_utf8_sig(self):
        text = history.dump_file([history.to_record(RUN, "1234-STD")], "1234-STD")
        raw = ("﻿" + text).encode("utf-8")
        runs = history.load_file(raw.decode("utf-8-sig"), "1234-STD")
        self.assertEqual(len(runs), 1)


if __name__ == "__main__":
    unittest.main()
