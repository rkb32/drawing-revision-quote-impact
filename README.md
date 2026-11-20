# Drawing Revision Quote Impact

**Prototype. Tested only on synthetic drawings. Not validated on real customer drawings.**

Give it an old and a new drawing PDF, a BOM, and a vendor quote sheet. It tells you which quote lines a revision makes stale, and it never says "no change" for a field it could not read.

## What it does

- Reads 14 fields from text, OCR'd scans and rotated sheets: stud length, thread, material, spec note, holes, quantity, diameter, nut, coating, tubing grade, NACE, tolerances, GD&T, general tolerance.
- Diffs the fields and cross-checks them against the revision block.
- Maps each change to BOM and quote lines and computes exposure per vendor. Vendors are never added together.
- Estimates material-only cost for a stud length change, from a price table you supply.
- Checks mill heat certs against a changed material, from a CSV you supply (RE-CERTIFY / OK / UNCHECKED).
- Draws boxes on changed regions and writes an Excel sheet, a markup PDF and a change-order draft.
- Drafts vendor reconfirm emails. Nothing is sent.

It does not read mill cert PDFs, price vendor markup or labor, or check that a quote is current.

## Run it

Command line:

```
python cli.py old.pdf new.pdf bom.csv quotes.csv --part 1234-STD --out out_run
```

Optional: `--prices prices.csv` (material price table) and `--certs certs.csv` (heat certs).

Batch (one folder of `old.pdf` / `new.pdf` pairs):

```
python batch.py ROOT bom.csv quotes.csv --part 1234-STD --out out_batch
```

Web app (local):

```
python hosted_app.py
```

Then open http://127.0.0.1:8080. It accepts optional price and cert CSVs. It keeps no files after it returns results.

Live sample page (synthetic data): https://rkb32.github.io/drawing-revision-quote-impact/

## Tests

```
python -m unittest discover -s tests
```

Tests use synthetic drawings only. Seeded single-field mutations are in `tests/test_mutations.py`.

## Status

See `DECISION.md`. No accuracy number exists yet. The next step is a real drawing pair with a known outcome.
