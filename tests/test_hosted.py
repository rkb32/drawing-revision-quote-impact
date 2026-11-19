import glob
import io
import os
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import hosted_app as h  # noqa: E402

S = os.path.join(HERE, "samples")


def leftovers():
    tmp = tempfile.gettempdir()
    return set(glob.glob(os.path.join(tmp, "revimpact_*")))


class Hosted(unittest.TestCase):
    def test_sample_route_returns_zip_with_results_and_no_leftovers(self):
        before = leftovers()
        c = h.app.test_client()
        r = c.post("/sample")
        self.assertEqual(r.status_code, 200)
        z = zipfile.ZipFile(io.BytesIO(r.data))
        names = set(z.namelist())
        self.assertIn("summary.txt", names)
        self.assertIn("impact.xlsx", names)
        self.assertIn("markup.pdf", names)
        self.assertIn("Policy:", z.read("summary.txt").decode())
        self.assertEqual(leftovers(), before, "temp folders left behind")

    def test_upload_route_cleans_up_on_success(self):
        before = leftovers()
        c = h.app.test_client()
        with open(os.path.join(S, "drawing_revA.pdf"), "rb") as A, open(os.path.join(S, "drawing_revB.pdf"), "rb") as B, \
             open(os.path.join(S, "bom.csv"), "rb") as M, open(os.path.join(S, "quotes.csv"), "rb") as Q:
            r = c.post("/run", data={"old": (A, "a.pdf"), "new": (B, "b.pdf"), "bom": (M, "bom.csv"),
                                     "quotes": (Q, "q.csv"), "part": "1234-STD"},
                       content_type="multipart/form-data")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(leftovers(), before)

    def test_temp_folder_removed_even_when_processing_fails(self):
        before = leftovers()
        c = h.app.test_client()
        with open(os.path.join(S, "drawing_revA.pdf"), "rb") as A, open(os.path.join(S, "drawing_revB.pdf"), "rb") as B, \
             open(os.path.join(S, "bom.csv"), "rb") as M, open(os.path.join(S, "quotes.csv"), "rb") as Q:
            orig = h.impact.run

            def boom(*a, **k):
                raise RuntimeError("forced failure")
            h.impact.run = boom
            try:
                r = c.post("/run", data={"old": (A, "a.pdf"), "new": (B, "b.pdf"), "bom": (M, "bom.csv"),
                                         "quotes": (Q, "q.csv"), "part": "1234-STD"},
                           content_type="multipart/form-data")
            finally:
                h.impact.run = orig
        self.assertEqual(r.status_code, 500)
        self.assertEqual(leftovers(), before)

    def test_bad_file_type_rejected(self):
        c = h.app.test_client()
        r = c.post("/run", data={"old": (io.BytesIO(b"x"), "a.exe"), "new": (io.BytesIO(b"x"), "b.pdf"),
                                 "bom": (io.BytesIO(b"x"), "b.csv"), "quotes": (io.BytesIO(b"x"), "q.csv"),
                                 "part": "P"}, content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)

    def test_policy_visible_before_upload(self):
        body = h.app.test_client().get("/").get_data(as_text=True)
        self.assertIn("deleted as soon as your results are returned", body)
        self.assertLess(body.index("deleted as soon"), body.index('type="file"'))

    def test_oversize_upload_rejected(self):
        c = h.app.test_client()
        h.app.config["MAX_CONTENT_LENGTH"] = 1000
        try:
            r = c.post("/run", data={"old": (io.BytesIO(b"x" * 5000), "a.pdf")}, content_type="multipart/form-data")
        finally:
            h.app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
        self.assertEqual(r.status_code, 413)


if __name__ == "__main__":
    unittest.main()
