"""Tests for the heat-cert check on revision. Synthetic inputs only."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import heat_check as hc  # noqa: E402

CHANGE = [{"field": "material", "old": "A193 B7", "new": "A320 L7"}]
CERTS = [
    {"part_no": "1234-STD", "piece_mark": "P-001", "heat_no": "H1", "cert_material": "a193 b7"},
    {"part_no": "1234-STD", "piece_mark": "P-002", "heat_no": "H2", "cert_material": "a320 l7"},
    {"part_no": "1234-STD", "piece_mark": "P-003", "heat_no": "H3", "cert_material": ""},
    {"part_no": "OTHER", "piece_mark": "X", "heat_no": "H9", "cert_material": "a193 b7"},
]


class HeatCheck(unittest.TestCase):
    def test_old_material_needs_recert(self):
        rows = {r["piece_mark"]: r for r in hc.check(CHANGE, CERTS, "1234-STD")}
        self.assertEqual(rows["P-001"]["status"], "RE-CERTIFY")

    def test_new_material_is_ok(self):
        rows = {r["piece_mark"]: r for r in hc.check(CHANGE, CERTS, "1234-STD")}
        self.assertEqual(rows["P-002"]["status"], "OK")

    def test_blank_cert_is_unchecked_not_ok(self):
        rows = {r["piece_mark"]: r for r in hc.check(CHANGE, CERTS, "1234-STD")}
        self.assertEqual(rows["P-003"]["status"], "UNCHECKED")

    def test_other_part_ignored_and_no_material_change_gives_nothing(self):
        self.assertNotIn("X", [r["piece_mark"] for r in hc.check(CHANGE, CERTS, "1234-STD")])
        self.assertEqual(hc.check([{"field": "holes", "old": "8", "new": "12"}], CERTS, "1234-STD"), [])


if __name__ == "__main__":
    unittest.main()
