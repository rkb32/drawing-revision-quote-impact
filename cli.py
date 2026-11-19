"""CLI: python cli.py old.pdf new.pdf bom.csv quotes.csv --part 1234-STD --out out_run

Exit codes: 0 = all fields read and every change priced or flagged.
            1 = at least one field could not be read (UNCHECKED). Do not trust "no impact".
            2 = bad input.
"""
import argparse
import sys

from impact import run


def main(argv=None):
    p = argparse.ArgumentParser(description="Drawing revision -> quote impact")
    p.add_argument("old_pdf")
    p.add_argument("new_pdf")
    p.add_argument("bom_csv")
    p.add_argument("quotes_csv")
    p.add_argument("--part", required=True, help="BOM part number to price")
    p.add_argument("--out", default="out_run")
    p.add_argument("--vendor", default=None, help="show the total for one vendor only")
    args = p.parse_args(argv)
    try:
        s = run(args.old_pdf, args.new_pdf, args.bom_csv, args.quotes_csv, args.part, args.out)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"changes: {s['changes']}  unpriced rows: {s['unpriced_rows']}")
    print("priced exposure, one vendor at a time (vendors are not summed):")
    for vendor, amt in s["priced_exposure_by_vendor_usd"].items():
        print(f"  {vendor}: ${amt}")
    print(f"raster boxes: {s['raster_boxes']}  shift px: {s['raster_shift_px']}")
    if args.vendor:
        amt = s["priced_exposure_by_vendor_usd"].get(args.vendor)
        print(f"total for {args.vendor}: {'$' + str(amt) if amt is not None else 'no priced rows'}")
    for c in s["changes_with_location"]:
        print(f"  {c['field']}: {c['old']} -> {c['new']}  new loc: {c['loc_new']}")
    if s["unchecked_fields"]:
        print("UNCHECKED (could not read on one side):")
        for u in s["unchecked_fields"]:
            print(f"  {u['field']}: rev_A={u['rev_A']} rev_B={u['rev_B']}")
        return 1
    print(f"output: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
