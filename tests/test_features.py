"""Tests for rev guard, overlay, batch, history and DXF diff. Synthetic inputs only."""
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import batch  # noqa: E402
import dxf_diff  # noqa: E402
import history  # noqa: E402
import impact  # noqa: E402

SAMPLES = os.path.join(HERE, "samples")
REV_A = os.path.join(SAMPLES, "drawing_revA.pdf")
REV_B = os.path.join(SAMPLES, "drawing_revB.pdf")
BOM = os.path.join(SAMPLES, "bom.csv")
QUOTES = os.path.join(SAMPLES, "quotes.csv")


class RevGuard(unittest.TestCase):
    def test_no_rev_column_is_flagged_not_passed(self):
        g = impact.rev_guard([{"vendor": "V", "part_no": "1234-STD"}], "1234-STD", REV_B)
        self.assertEqual(g[0]["status"], "QUOTE HAS NO REV")

    def test_old_rev_is_flagged(self):
        g = impact.rev_guard([{"vendor": "V", "part_no": "1234-STD", "rev": "A"}], "1234-STD", REV_B)
        self.assertEqual(g[0]["status"], "QUOTE ON OLD REV")

    def test_current_rev_passes(self):
        g = impact.rev_guard([{"vendor": "V", "part_no": "1234-STD", "rev": "b"}], "1234-STD", REV_B)
        self.assertEqual(g, [])

    def test_other_part_ignored(self):
        g = impact.rev_guard([{"vendor": "V", "part_no": "OTHER", "rev": "A"}], "1234-STD", REV_B)
        self.assertEqual(g, [])


class Overlay(unittest.TestCase):
    def test_overlay_written(self):
        d = tempfile.mkdtemp()
        try:
            out = impact.write_overlay(REV_A, REV_B, os.path.join(d, "o.png"))
            self.assertTrue(os.path.getsize(out) > 0)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class Batch(unittest.TestCase):
    def test_batch_runs_each_pair(self):
        root, out = tempfile.mkdtemp(), tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(root, "job1"))
            shutil.copy(REV_A, os.path.join(root, "job1", "old.pdf"))
            shutil.copy(REV_B, os.path.join(root, "job1", "new.pdf"))
            path, lines = batch.run_batch(root, BOM, QUOTES, "1234-STD", os.path.join(out, "b"))
            self.assertTrue(os.path.exists(path))
            self.assertEqual(lines[0]["status"], "ok")
            self.assertEqual(lines[0]["changes"], 3)
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(out, ignore_errors=True)

    def test_empty_root_raises(self):
        d = tempfile.mkdtemp()
        try:
            with self.assertRaises(FileNotFoundError):
                batch.run_batch(d, BOM, QUOTES, "1234-STD", tempfile.mkdtemp())
        finally:
            shutil.rmtree(d, ignore_errors=True)


class History(unittest.TestCase):
    def test_round_trip(self):
        d = tempfile.mkdtemp()
        db = os.path.join(d, "h.sqlite")
        try:
            s = {"new_rev": "B", "changes_with_location": [{"field": "holes"}],
                 "priced_exposure_by_vendor_usd": {"V": 1.5}, "rev_guard": []}
            history.save(s, "1234-STD", "A", path=db)
            h = history.history("1234-STD", path=db)
            self.assertEqual(h[0]["new_rev"], "B")
            self.assertEqual(h[0]["changes"], ["holes"])
            self.assertEqual(history.history("OTHER", path=db), [])
        finally:
            shutil.rmtree(d, ignore_errors=True)


class DxfDiff(unittest.TestCase):
    def test_added_text_detected(self):
        import ezdxf
        d = tempfile.mkdtemp()
        try:
            doc = ezdxf.new()
            doc.modelspace().add_line((0, 0), (10, 0))
            doc.saveas(os.path.join(d, "o.dxf"))
            doc = ezdxf.new()
            doc.modelspace().add_line((0, 0), (10, 0))
            doc.modelspace().add_text("NOTE", dxfattribs={"insert": (1, 1)})
            doc.saveas(os.path.join(d, "n.dxf"))
            added, removed, u_old, u_new = dxf_diff.diff(os.path.join(d, "o.dxf"), os.path.join(d, "n.dxf"))
            self.assertEqual(len(added), 1)
            self.assertEqual(added[0][0][0], "TEXT")
            self.assertEqual(removed, [])
            self.assertEqual((u_old, u_new), (0, 0))
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
