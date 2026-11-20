"""Seeded single-field mutations on the synthetic CAD sheet. Each change must show as a
change or as UNCHECKED, never as silence. Synthetic values only; writes to a temp folder."""
import copy
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import impact as I  # noqa: E402
import make_cad_pairs as M  # noqa: E402

MUTATIONS = {
    "stud_len": {"stud_len": "6.00 in"},
    "material": {"material": "A320 L7"},
    "holes": {"holes": "16"},
    "qty": {"qty": "30"},
    "diameter": {"diameter": "1.250 in"},
    "thread": {"thread": "1-12 UNF-2A"},
    "spec_note": {"spec": "ASTM A320 GR L7"},
    "tubing_grade": {"grade": "Grade B or C"},
    "nut": {"nut": "A194 7"},
    "coating": {"coating": "PTFE"},
}


class Mutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="mut_")
        base = dict(M.REV["A"])
        a_dxf, a_pdf = os.path.join(cls.tmp, "a.dxf"), os.path.join(cls.tmp, "a.pdf")
        M.build_dxf("A", base, a_dxf)
        M.dxf_to_pdf(a_dxf, a_pdf)
        cls.a = I.extract(a_pdf)
        cls.results = {}
        for name, change in list(MUTATIONS.items()) + [("no_change", {})]:
            d = copy.deepcopy(base)
            d.update(change)
            b_dxf, b_pdf = os.path.join(cls.tmp, f"{name}.dxf"), os.path.join(cls.tmp, f"{name}.pdf")
            M.build_dxf("B", d, b_dxf)
            M.dxf_to_pdf(b_dxf, b_pdf)
            cls.results[name] = I.diff(cls.a, I.extract(b_pdf))

    def test_each_mutation_is_reported_as_a_change(self):
        for name in MUTATIONS:
            changes, _ = self.results[name]
            self.assertIn(name, [c["field"] for c in changes], name)

    def test_no_change_pair_reports_no_change(self):
        changes, _ = self.results["no_change"]
        self.assertEqual(changes, [])


if __name__ == "__main__":
    unittest.main()
