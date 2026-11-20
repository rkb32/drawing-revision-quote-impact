"""CLI: python cli.py old.pdf new.pdf bom.csv quotes.csv --part 1234-STD --out out_run

Exit codes: 0 = all fields read and every change priced or flagged.
            1 = at least one field could not be read (UNCHECKED). Do not trust "no impact".
            2 = bad input.
"""
import argparse
import sys

from impact import latest_rev, run


def main(argv=None):
    p = argparse.ArgumentParser(description="Drawing revision -> quote impact")
    p.add_argument("old_pdf")
    p.add_argument("new_pdf")
    p.add_argument("bom_csv")
    p.add_argument("quotes_csv")
    p.add_argument("--part", required=True, help="BOM part number to price")
    p.add_argument("--out", default="out_run")
    p.add_argument("--vendor", default=None, help="show the total for one vendor only")
    p.add_argument("--prices", default=None, help="price table CSV (material, usd_per_lb_low, usd_per_lb_high, source)")
    p.add_argument("--certs", default=None, help="heat-cert CSV (part_no, piece_mark, heat_no, cert_material)")
    p.add_argument("--show-history", action="store_true", help="print saved runs for this part (local revisions.sqlite)")
    p.add_argument("--history", action="store_true", help="save this run to revisions.sqlite (local only)")
    args = p.parse_args(argv)
    if args.show_history:
        import history
        for h in history.history(args.part):
            print(f"{h['created']}  {h['old_rev']} -> {h['new_rev']}  changes: {', '.join(h['changes']) or 'none'}  exposure: {h['exposure_by_vendor']}")
        return 0
    try:
        s = run(args.old_pdf, args.new_pdf, args.bom_csv, args.quotes_csv, args.part, args.out,
                prices_csv=args.prices, heat_certs_csv=args.certs)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.history:
        import history
        history.save(s, args.part, latest_rev(args.old_pdf))
        print("saved to revisions.sqlite")
    print(f"changes: {s['changes']}  unpriced rows: {s['unpriced_rows']}")
    for g in s["rev_guard"]:
        print(f"REV GUARD {g['vendor']}: {g['status']} ({g['detail']})")
    print("priced exposure, one vendor at a time (vendors are not summed):")
    for vendor, amt in s["priced_exposure_by_vendor_usd"].items():
        print(f"  {vendor}: ${amt}")
    hc = s["heat_cert"]
    print(f"heat cert: {hc if isinstance(hc, str) else ('none' if not hc else [r['status'] for r in hc])}")
    if s["uncovered_text_warning"]:
        print("WARNING: " + s["uncovered_text_warning"])
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
