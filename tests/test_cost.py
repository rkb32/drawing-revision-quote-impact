"""Tests for cost delta. Synthetic inputs only."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import cost_delta as cd  # noqa: E402

PRICES = [{"material": "*", "usd_per_lb_low": "0.59", "usd_per_lb_high": "0.63", "source": "test"}]


class DiameterRule(unittest.TestCase):
    def _find(self, text):
        import re
        import impact
        m = re.search(impact.RULES["fields"]["diameter"]["pattern"], text, flags=re.IGNORECASE)
        return m.group(1).strip() if m else None

    def test_stud_diameter_line_matches(self):
        self.assertEqual(self._find("Stud length: 5 in\nDiameter: 1.125 in\nMaterial: A320"), "1.125 in")

    def test_pitch_diameter_does_not_match(self):
        self.assertIsNone(self._find("PITCH DIAMETER: 2.500 in\nBOLT CIRCLE DIAMETER 3.0"))


class ParseInches(unittest.TestCase):
    def test_forms(self):
        self.assertAlmostEqual(cd.parse_inches("5.00 in"), 5.0)
        self.assertAlmostEqual(cd.parse_inches("1-1/8"), 1.125)
        self.assertAlmostEqual(cd.parse_inches("1 1/2\""), 1.5)
        self.assertAlmostEqual(cd.parse_inches("1/2"), 0.5)

    def test_unreadable_is_none(self):
        self.assertIsNone(cd.parse_inches(None))
        self.assertIsNone(cd.parse_inches("M24 x 3"))


class StudLengthDelta(unittest.TestCase):
    def test_arithmetic(self):
        # 4 in -> 5 in, 1.125 in dia, qty 24
        lb_per_in = 0.2836 * 3.141592653589793 / 4 * 1.125 ** 2
        r = cd.stud_length_delta({"old": "4.00 in", "new": "5.00 in"}, 24, "1.125 in", PRICES, "a320 l7")
        exact_lb = 1 * lb_per_in * 24
        self.assertAlmostEqual(r["delta_lb"], round(exact_lb, 2), places=2)
        self.assertAlmostEqual(r["delta_usd_low"], round(exact_lb * 0.59, 2), places=2)
        self.assertAlmostEqual(r["delta_usd_high"], round(exact_lb * 0.63, 2), places=2)
        self.assertTrue(r["status"].startswith("priced"))

    def test_missing_diameter_unpriced_not_zero(self):
        r = cd.stud_length_delta({"old": "4", "new": "5"}, 24, None, PRICES, "x")
        self.assertEqual(r["status"], "unpriced: stud diameter not read")
        self.assertNotIn("delta_usd_low", r)

    def test_missing_bom_unpriced(self):
        r = cd.stud_length_delta({"old": "4", "new": "5"}, None, "1 in", PRICES, "x")
        self.assertEqual(r["status"], "unpriced: part not in BOM or qty is zero")

    def test_no_price_row_unpriced(self):
        r = cd.stud_length_delta({"old": "4", "new": "5"}, 2, "1 in", [], "x")
        self.assertEqual(r["status"], "unpriced: no price row for this material")


if __name__ == "__main__":
    unittest.main()
