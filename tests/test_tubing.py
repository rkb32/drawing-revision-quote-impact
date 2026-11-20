"""tubing_grade rule: interleaved two-column text and normal reading order. Synthetic text only."""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

with open(os.path.join(HERE, "rules.json"), encoding="utf-8") as _f:
    PATTERN = json.load(_f)["fields"]["tubing_grade"]["pattern"]

OLD_INTERLEAVED = "Grade B.  Paint all metal components\nFurnish structural tubing for rails conforming to ASTM A500,\n"
NEW_INTERLEAVED = "Grade B or C.  Paint all metal components\nProvide structural tubing for rails conforming to ASTM A500,\n"
OLD_NORMAL = "Furnish structural tubing for rails conforming to ASTM A500, Grade B.\n"
NEW_NORMAL = "Provide structural tubing for rails conforming to ASTM A500, Grade B or C.\n"


def grade(text):
    m = re.search(PATTERN, text, flags=re.IGNORECASE)
    return None if m is None else " ".join(next((g for g in m.groups() if g), m.group(0)).split()).lower()


class TubingGrade(unittest.TestCase):
    def test_interleaved_layout(self):
        self.assertEqual(grade(OLD_INTERLEAVED), "grade b")
        self.assertEqual(grade(NEW_INTERLEAVED), "grade b or c")

    def test_normal_reading_order(self):
        self.assertEqual(grade(OLD_NORMAL), "grade b")
        self.assertEqual(grade(NEW_NORMAL), "grade b or c")

    def test_absent_note_is_none_not_a_value(self):
        self.assertIsNone(grade("STUD ASSEMBLY - PART 1234-STD\nStud length: 4.00 in\n"))


if __name__ == "__main__":
    unittest.main()
