import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import impact  # noqa: E402
import cli  # noqa: E402

S = os.path.join(HERE, "samples")
A = os.path.join(S, "drawing_revA.pdf")
B = os.path.join(S, "drawing_revB.pdf")
BOM = os.path.join(S, "bom.csv")
Q = os.path.join(S, "quotes.csv")
VA = os.path.join(HERE, "samples_variant", "variant_revA.pdf")
VB = os.path.join(HERE, "samples_variant", "variant_revB.pdf")


class OriginalLayout(unittest.TestCase):
    def test_fields_present_on_original_are_found(self):
        for pdf in (A, B):
            e = impact.extract(pdf)
            for f in ("stud_len", "material", "holes", "qty"):
                self.assertEqual(e.status[f], "FOUND", (pdf, f))

    def test_changes_and_absent_fields_are_unchecked(self):
        changes, unchecked = impact.diff(impact.extract(A), impact.extract(B))
        self.assertEqual(sorted(c["field"] for c in changes), ["holes", "material", "stud_len"])
        # thread and spec_note are not on the original layout: UNCHECKED, never "no change"
        self.assertEqual(sorted(u["field"] for u in unchecked),
                         ["coating", "diameter", "nut", "spec_note", "thread"])

    def test_cross_check_clean_on_original(self):
        changes, _ = impact.diff(impact.extract(A), impact.extract(B))
        self.assertEqual(impact.cross_check(changes, A, B), [])

    def test_priced_exposure_is_per_vendor_never_summed(self):
        with tempfile.TemporaryDirectory() as d:
            s = impact.run(A, B, BOM, Q, "1234-STD", d)
        # stud_len requote, qty 24: VendorX 1.05*24, VendorY 1.15*24, VendorZ 1.25*24
        self.assertEqual(s["priced_exposure_by_vendor_usd"],
                         {"VendorX": 25.20, "VendorY": 27.60, "VendorZ": 30.00})
        self.assertEqual(s["priced_exposure_range_usd"], (25.20, 30.00))
        self.assertEqual(s["unpriced_rows"], 0)

    def test_unknown_part_is_unpriced_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            s = impact.run(A, B, BOM, Q, "NOPE-000", d)
        self.assertEqual(s["priced_exposure_by_vendor_usd"], {})
        self.assertTrue(all(r["status"].startswith("unpriced") for r in s["rows"]))

    def test_unreadable_field_is_unchecked_not_no_change(self):
        a, b = impact.extract(A), impact.extract(B)
        b.status["holes"] = "NOT FOUND"
        b.values["holes"] = None
        changes, unchecked = impact.diff(a, b)
        self.assertIn("holes", [u["field"] for u in unchecked])
        self.assertNotIn("holes", [c["field"] for c in changes])

    def test_cli_exit_1_when_unchecked(self):
        orig = impact.RULES["fields"]["holes"]["pattern"]
        impact.RULES["fields"]["holes"]["pattern"] = "NOT_IN_DRAWING_XYZ(\\d+)"
        try:
            with tempfile.TemporaryDirectory() as d:
                code = cli.main([A, B, BOM, Q, "--part", "1234-STD", "--out", d])
        finally:
            impact.RULES["fields"]["holes"]["pattern"] = orig
        self.assertEqual(code, 1)


class ScanAndRotation(unittest.TestCase):
    def test_scanned_sheet_read_by_ocr(self):
        e = impact.extract(os.path.join(HERE, "samples_scan", "scan_revB.pdf"))
        self.assertEqual(e.values["stud_len"], "5.00 in")
        self.assertEqual(e.values["holes"], "12")
        self.assertTrue(e.status["stud_len"].endswith("(OCR)"))

    def test_rotated_sheet_read_correctly(self):
        e = impact.extract(os.path.join(HERE, "samples_scan", "rot_revB.pdf"))
        self.assertEqual(e.values["stud_len"], "5.00 in")
        self.assertEqual(e.values["material"], "a320 l7")

    def test_shifted_sheet_gives_no_false_boxes(self):
        boxes, shift = impact.raster_regions(B, os.path.join(HERE, "samples_scan", "shift_revB.pdf"))
        self.assertEqual(len(boxes), 0)

    def test_real_change_still_boxed(self):
        boxes, _ = impact.raster_regions(A, B)
        self.assertGreater(len(boxes), 0)


class GdtLayout(unittest.TestCase):
    GA = os.path.join(HERE, "samples_gdt", "gdt_revA.pdf")
    GB = os.path.join(HERE, "samples_gdt", "gdt_revB.pdf")

    def test_position_tolerance_change_detected(self):
        changes, _ = impact.diff(impact.extract(self.GA), impact.extract(self.GB))
        self.assertIn("gdt", [c["field"] for c in changes])

    def test_block_mentions_tolerance_so_no_mismatch_for_gdt(self):
        changes, _ = impact.diff(impact.extract(self.GA), impact.extract(self.GB))
        flags = impact.cross_check(changes, self.GA, self.GB)
        self.assertNotIn(("NOT IN REVISION BLOCK", "gdt"), [(f["type"], f["field"]) for f in flags])


class GdtSymbols(unittest.TestCase):
    SA = os.path.join(HERE, "samples_gdt_sym", "sym_revA.pdf")
    SB = os.path.join(HERE, "samples_gdt_sym", "sym_revB.pdf")

    def test_symbol_frame_change_detected(self):
        changes, _ = impact.diff(impact.extract(self.SA), impact.extract(self.SB))
        self.assertIn("gdt", [c["field"] for c in changes])

    def test_symbol_change_is_located_on_sheet(self):
        self.assertIsNotNone(impact.locate(self.SB, "ø0.002"))


class VariantLayout(unittest.TestCase):
    def test_variant_finds_length_thread_and_spec_note_not_material(self):
        changes, unchecked = impact.diff(impact.extract(VA), impact.extract(VB))
        self.assertEqual(sorted(c["field"] for c in changes), ["spec_note", "stud_len", "thread"])
        # diameter, nut and coating are not on this layout: UNCHECKED, not "no change"
        self.assertEqual(sorted(u["field"] for u in unchecked), ["coating", "diameter", "nut"])

    def test_variant_revision_block_agrees_with_diff(self):
        changes, _ = impact.diff(impact.extract(VA), impact.extract(VB))
        self.assertEqual(impact.cross_check(changes, VA, VB), [])

    def test_block_claim_without_diff_is_flagged(self):
        changes, _ = impact.diff(impact.extract(VA), impact.extract(VB))
        pruned = [c for c in changes if c["field"] != "stud_len"]
        flags = impact.cross_check(pruned, VA, VB)
        self.assertIn(("BLOCK CLAIM NOT FOUND IN DRAWING", "stud_len"),
                      [(f["type"], f["field"]) for f in flags])


if __name__ == "__main__":
    unittest.main()
