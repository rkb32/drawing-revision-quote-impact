import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import app as webapp  # noqa: E402


class WebForm(unittest.TestCase):
    def test_index_and_run_and_download(self):
        c = webapp.app.test_client()
        self.assertEqual(c.get("/").status_code, 200)
        S = os.path.join(HERE, "samples")
        with open(os.path.join(S, "drawing_revA.pdf"), "rb") as A, \
             open(os.path.join(S, "drawing_revB.pdf"), "rb") as B, \
             open(os.path.join(S, "bom.csv"), "rb") as M, \
             open(os.path.join(S, "quotes.csv"), "rb") as Q:
            r = c.post("/run", data={"old": (A, "a.pdf"), "new": (B, "b.pdf"),
                                     "bom": (M, "bom.csv"), "quotes": (Q, "quotes.csv"),
                                     "part": "1234-STD"}, content_type="multipart/form-data")
        body = r.get_data(as_text=True)
        self.assertIn("Done.", body)
        link = re.search(r"/files/[0-9a-f]+/impact\.xlsx", body).group(0)
        self.assertEqual(c.get(link).status_code, 200)

    def test_bad_file_name_rejected(self):
        c = webapp.app.test_client()
        self.assertEqual(c.get("/files/abc/secret.txt").status_code, 404)


if __name__ == "__main__":
    unittest.main()
