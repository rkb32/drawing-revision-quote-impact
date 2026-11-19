# Outreach drafts (NOT SENT. Review and send yourself.)

## 1. Message to Berni (one bundled ask)
Hi Berni,

I'm building a small tool that flags which vendor quotes go stale when a drawing revision comes in. I've tested it on synthetic drawings only. Could I ask for three small things?

1. One closed past job with a revision: both drawing PDFs, the BOM, and the quote sheet. Prices and customer names can be blacked out.
2. Column headers only from your ERP quote or PO export (no values).
3. 20 minutes on a screen share, where you or an estimator does one real revision by hand while I time it.

Happy to share the results with you first. Thanks,
[name]

## 2. Message to a shop admin (headers only)
Hi [name], could you export one purchase order or quote from JobBOSS to CSV and send me only the column headers (the first row, no values)? That's all I need to map the fields. Thanks, [name]

## 3. Estimator pilot script (20 min)
1. Pick one past revision with a known answer.
2. Estimator does it by hand. Time it (start: both files open; stop: list of affected quote lines written down).
3. Run `python cli.py old.pdf new.pdf bom.csv quotes.csv --part <PN> --out run` and time it.
4. Compare the two lists. Write down every miss and every false flag.

## Public list price check (no contact needed)
- A320 L7 at the same size as A193 B7: not found on Grainger, Fastenal or Zoro-equivalent pages in this search. Zoro shows one L7 2-1/4" stud at $2.78 each, a different length and quantity. Not like-for-like.
