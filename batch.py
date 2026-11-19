"""Batch run: one folder of revision pairs against one BOM and one quote sheet.

Layout: ROOT/<job name>/old.pdf and ROOT/<job name>/new.pdf (one subfolder per pair).
Run:    python batch.py ROOT bom.csv quotes.csv --part 1234-STD --out out_batch
Writes: OUT/<job name>/ (same files as a single run) and OUT/batch_summary.csv
"""
import argparse
import csv
import os
import sys

from impact import run


def find_jobs(root):
    jobs = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        old, new = os.path.join(d, "old.pdf"), os.path.join(d, "new.pdf")
        if os.path.isdir(d) and os.path.exists(old) and os.path.exists(new):
            jobs.append((name, old, new))
    return jobs


def run_batch(root, bom_csv, quotes_csv, part_no, out_root):
    jobs = find_jobs(root)
    if not jobs:
        raise FileNotFoundError(f"no job folders with old.pdf and new.pdf under {root}")
    os.makedirs(out_root, exist_ok=True)
    lines = []
    for name, old, new in jobs:
        try:
            s = run(old, new, bom_csv, quotes_csv, part_no, os.path.join(out_root, name))
            lines.append({"job": name, "status": "ok", "changes": s["changes"],
                          "unpriced_rows": s["unpriced_rows"],
                          "unchecked": len(s["unchecked_fields"]),
                          "rev_guard_flags": len(s["rev_guard"]),
                          "new_rev": s["new_rev"] or "",
                          "exposure_by_vendor": "; ".join(f"{v}={a}" for v, a in s["priced_exposure_by_vendor_usd"].items())})
        except Exception as e:  # one bad pair must not stop the batch
            lines.append({"job": name, "status": f"ERROR: {type(e).__name__}: {e}", "changes": "", "unpriced_rows": "",
                          "unchecked": "", "rev_guard_flags": "", "new_rev": "", "exposure_by_vendor": ""})
    path = os.path.join(out_root, "batch_summary.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lines[0].keys()))
        w.writeheader()
        w.writerows(lines)
    return path, lines


def main(argv=None):
    p = argparse.ArgumentParser(description="Batch revision -> quote impact")
    p.add_argument("root")
    p.add_argument("bom_csv")
    p.add_argument("quotes_csv")
    p.add_argument("--part", required=True)
    p.add_argument("--out", default="out_batch")
    args = p.parse_args(argv)
    try:
        path, lines = run_batch(args.root, args.bom_csv, args.quotes_csv, args.part, args.out)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    bad = sum(1 for r in lines if r["status"] != "ok")
    print(f"jobs: {len(lines)}  errors: {bad}  summary: {path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
