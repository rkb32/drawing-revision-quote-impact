# Drawing Revision Quote Impact

**Prototype. Tested only on synthetic drawings. Not validated on real customer drawings.**

Given an old and new drawing PDF, a BOM, and a vendor quote sheet, it:

- reads about a dozen fields from text, OCR'd scans and rotated sheets
- diffs the fields and cross-checks the revision block
- maps each change to BOM and quote lines and computes per-vendor exposure (vendors are never summed)
- flags changes it cannot price, and fields it cannot read (UNCHECKED, never "no change")
- draws boxes on changed regions and writes an Excel sheet
- drafts vendor reconfirm emails (drafts only, nothing is sent)

It does not price engineering time or material cost, and it does not parse real GD&T frames.

## Run

```
python cli.py old.pdf new.pdf bom.csv quotes.csv --part 1234-STD --out out_run
```

Tests: `python -m unittest discover -s tests`

## Status

See `DECISION.md`. No accuracy number exists yet.
