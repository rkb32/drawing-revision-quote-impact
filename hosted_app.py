"""Hosted version: stateless. Each request gets a temp folder that is deleted in a finally block.
Nothing is written to a persistent location. Results come back as one zip file.
Learning/decision logging is not used here.

Run locally to test:  python hosted_app.py   (http://127.0.0.1:8080)
"""
import html
import io
import os
import shutil
import tempfile
import zipfile

from flask import Flask, abort, request, send_file

import changeorder
import impact

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "samples")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB total upload limit

POLICY = ("Your files are sent over an encrypted (HTTPS) connection to the server, processed, "
          "and deleted as soon as your results are returned. We do not keep, view, or share them. "
          "This is a free early tool with no security certification. If your contract forbids sending "
          "a customer's drawings to third parties, do not upload them: use the sample files, or run "
          "the tool on your own computer (instructions are in the GitHub README).")

FORM = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Revision Impact</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:720px;margin:24px auto;padding:0 16px;color:#1d1d1b}}
.box{{border:1px solid #e4e2da;border-radius:8px;padding:14px;margin:12px 0}}
.policy{{background:#fff7e6;border-left:3px solid #b36b00;padding:8px 12px;font-size:.92rem}}
button{{padding:9px 18px;font-size:15px;margin-right:8px}}</style></head><body>
<h1>Drawing revision impact</h1>
<p>Upload the old and new drawing, the BOM and the quote sheet. Get back an Excel sheet, a marked-up PDF and a change-order draft.</p>
<p class="policy">{html.escape(POLICY)}</p>
<form method="post" action="/run" enctype="multipart/form-data"><div class="box">
<div>Old drawing (PDF): <input type="file" name="old" accept=".pdf" required></div>
<div>New drawing (PDF): <input type="file" name="new" accept=".pdf" required></div>
<div>BOM (CSV or XLSX): <input type="file" name="bom" accept=".csv,.xlsx" required></div>
<div>Quote sheet (CSV or XLSX): <input type="file" name="quotes" accept=".csv,.xlsx" required></div>
<div>Price table (optional CSV): <input type="file" name="prices" accept=".csv"></div>
<div>Heat certs (optional CSV): <input type="file" name="certs" accept=".csv"></div>
<div>Part number to price: <input type="text" name="part" value="1234-STD" required></div>
<p><button type="submit">Run on my files</button></p></div></form>
<form method="post" action="/sample"><p><button type="submit">Try with sample files (nothing uploaded)</button></p></form>
</body></html>"""


def _run_and_zip(paths, part):
    work = tempfile.mkdtemp(prefix="revimpact_")
    try:
        out = os.path.join(work, "out")
        s = impact.run(paths["old"], paths["new"], paths["bom"], paths["quotes"], part, out,
                       prices_csv=paths.get("prices"), heat_certs_csv=paths.get("certs"))
        summary = [f"Changes: {s['changes']}", f"Unpriced rows: {s['unpriced_rows']}",
                   "Priced exposure per vendor (not added together):"]
        summary += [f"  {v}: ${a:.2f}" for v, a in s["priced_exposure_by_vendor_usd"].items()]
        summary += ["", "UNCHECKED (could not read on one side, NOT 'no change'):"]
        summary += [f"  {u['field']}: rev A {u['rev_A']}, rev B {u['rev_B']}" for u in s["unchecked_fields"]] or ["  none"]
        summary += ["", "Stud length cost (material only):"]
        summary += [f"  {c.get('status', c)}" for c in s["cost_delta"]] or ["  no stud length change"]
        hc = s["heat_cert"]
        summary += ["", "Heat certs: " + (hc if isinstance(hc, str) else ("none" if not hc else ", ".join(f"{r['piece_mark']}={r['status']}" for r in hc)))]
        summary += ["", "Revision check (quote vs new drawing revision):"]
        summary += [f"  {g['vendor']}: {g['status']} ({g['detail']})" for g in s["rev_guard"]] or ["  none"]
        if s["uncovered_text_warning"]:
            summary += ["", "WARNING: " + s["uncovered_text_warning"]]
        summary += ["", "Policy: " + POLICY]
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("summary.txt", "\n".join(summary) + "\n")
            for name in ("impact.xlsx", "markup.pdf", "overlay.png", "change_order_draft.md", "drafts.md", "summary.json",
                         "change_report.pdf", "change_report.csv"):
                p = os.path.join(out, name)
                if os.path.exists(p):
                    z.write(p, name)
        buf.seek(0)
        return send_file(buf, mimetype="application/zip", as_attachment=True, download_name="revision_impact_results.zip")
    finally:
        shutil.rmtree(work, ignore_errors=True)


@app.get("/")
def index():
    return FORM


@app.post("/run")
def run():
    work = tempfile.mkdtemp(prefix="revimpact_in_")
    try:
        paths = {}
        for key in ("old", "new", "bom", "quotes", "prices", "certs"):
            f = request.files.get(key)
            if not f or not f.filename:
                if key in ("prices", "certs"):
                    continue
                abort(400, f"missing {key}")
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in ((".csv",) if key in ("prices", "certs") else (".pdf", ".csv", ".xlsx")):
                abort(400, f"unsupported file type for {key}")
            p = os.path.join(work, f"{key}{ext}")
            f.save(p)
            paths[key] = p
        part = (request.form.get("part") or "").strip()
        if not part:
            abort(400, "missing part number")
        return _run_and_zip(paths, part)
    finally:
        shutil.rmtree(work, ignore_errors=True)


@app.post("/sample")
def sample():
    paths = {"old": os.path.join(SAMPLES, "drawing_revA.pdf"), "new": os.path.join(SAMPLES, "drawing_revB.pdf"),
             "bom": os.path.join(SAMPLES, "bom.csv"), "quotes": os.path.join(SAMPLES, "quotes.csv")}
    return _run_and_zip(paths, "1234-STD")


@app.errorhandler(413)
def too_big(_):
    return "File too large (limit 25 MB total). Split the upload or use a smaller file.", 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False)
