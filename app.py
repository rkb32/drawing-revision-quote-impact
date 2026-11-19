"""Local web form for the revision impact checker.

Binds to 127.0.0.1 only. Uploads are written to a temp folder that is deleted when the
server stops (or on the "Delete now" button). No outbound network calls are made.
"""
import atexit
import html
import os
import shutil
import tempfile
import uuid

from flask import Flask, abort, request, send_from_directory

import impact

app = Flask(__name__)
WORK = tempfile.mkdtemp(prefix="revimpact_")
atexit.register(lambda: shutil.rmtree(WORK, ignore_errors=True))

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revision Impact (local)</title>
<style>
body{font:15px/1.5 system-ui,Segoe UI,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#1d1d1b}
h1{font-size:1.4rem}.note{color:#5d5d58;font-size:.9rem}
table{border-collapse:collapse;width:100%;font-size:.9rem;margin:8px 0}
th,td{border-bottom:1px solid #e4e2da;padding:6px 8px;text-align:left}
.box{border:1px solid #e4e2da;border-radius:8px;padding:12px;margin:10px 0}
.warn{color:#b3261e}.ok{color:#1d6b2f}
input[type=file],input[type=text]{margin:4px 0}
button{padding:8px 16px;font-size:15px}
</style></head><body>
<h1>Revision Impact (runs on this PC only)</h1>
<p class="note">Files stay on this computer. No outbound connections. Working files are deleted when you close this window and stop the program.</p>
{body}
</body></html>"""

FORM = """<form method="post" action="/run" enctype="multipart/form-data">
<div class="box">
<div>Old drawing (PDF): <input type="file" name="old" accept=".pdf" required></div>
<div>New drawing (PDF): <input type="file" name="new" accept=".pdf" required></div>
<div>BOM (CSV or XLSX): <input type="file" name="bom" accept=".csv,.xlsx" required></div>
<div>Quote sheet (CSV or XLSX): <input type="file" name="quotes" accept=".csv,.xlsx" required></div>
<div>Part number to price: <input type="text" name="part" value="1234-STD" required></div>
<p><button type="submit">Run</button></p>
</div></form>"""


def page(body):
    return PAGE.replace("{body}", body)


def crop_png_b64(pdf_path, loc, w=260, h=40, dpi=150):
    """Small image of the text around a change location, or None if there is no location."""
    if not loc:
        return None
    import base64
    import pymupdf
    doc = pymupdf.open(pdf_path)
    pg = doc[loc["page"] - 1]
    x, y = loc["x"], loc["y"]
    clip = pymupdf.Rect(max(0, x - 8), max(0, y - 6), min(pg.rect.width, x + w), min(pg.rect.height, y + h))
    pix = pg.get_pixmap(dpi=dpi, clip=clip)
    return base64.b64encode(pix.tobytes("png")).decode()


@app.get("/")
def index():
    return page(FORM)


@app.post("/run")
def run():
    run_id = uuid.uuid4().hex[:10]
    d = os.path.join(WORK, run_id)
    os.makedirs(d, exist_ok=True)
    paths = {}
    for key in ("old", "new", "bom", "quotes"):
        f = request.files.get(key)
        if not f or not f.filename:
            abort(400, f"missing {key}")
        ext = os.path.splitext(f.filename)[1].lower()
        p = os.path.join(d, f"{key}{ext}")
        f.save(p)
        paths[key] = p
    part = (request.form.get("part") or "").strip()
    if not part:
        abort(400, "missing part number")

    s = impact.run(paths["old"], paths["new"], paths["bom"], paths["quotes"], part, d)

    rows = "".join(
        f"<tr><td>{html.escape(r['field'])}</td><td>{html.escape(str(r['old']))}</td>"
        f"<td>{html.escape(str(r['new']))}</td><td>{html.escape(r['action'])}</td>"
        f"<td>{html.escape(r['vendor'])}</td><td>{'' if r['exposure_usd'] is None else '$' + str(r['exposure_usd'])}</td>"
        f"<td>{html.escape(r['status'])}</td></tr>"
        for r in s["rows"]
    ) or "<tr><td colspan=7>No changes found.</td></tr>"
    unchecked = "".join(
        f"<li>{html.escape(u['field'])}: rev A {html.escape(str(u['rev_A']))}, rev B {html.escape(str(u['rev_B']))}</li>"
        for u in s["unchecked_fields"]
    ) or "<li>None. Every field was read on both drawings.</li>"
    vendors = "".join(
        f"<li>{html.escape(v)}: ${a:.2f}</li>" for v, a in s["priced_exposure_by_vendor_usd"].items()
    ) or "<li>No priced rows.</li>"

    crops = []
    for c in s["changes_with_location"]:
        old_img = crop_png_b64(paths["old"], c["loc_old"])
        new_img = crop_png_b64(paths["new"], c["loc_new"])
        old_tag = f'<img src="data:image/png;base64,{old_img}">' if old_img else "<i>no location (scan)</i>"
        new_tag = f'<img src="data:image/png;base64,{new_img}">' if new_img else "<i>no location (scan)</i>"
        crops.append(f"<tr><td>{html.escape(c['field'])}</td><td>{old_tag}</td><td>{new_tag}</td></tr>")
    crop_table = ("<table><tr><th>Field</th><th>Rev A</th><th>Rev B</th></tr>" + "".join(crops) + "</table>"
                  if crops else "<p class='note'>No changes to show.</p>")

    body = f"""<p class="ok"><b>Done.</b> {s['changes']} change(s). {s['unpriced_rows']} unpriced row(s).</p>
<div class="box"><b>Priced exposure, one vendor at a time (not added together)</b><ul>{vendors}</ul></div>
<h3>Where each change is on the sheet</h3>{crop_table}
<h3>Changes and affected quote rows</h3>
<table><tr><th>Field</th><th>Old</th><th>New</th><th>Action</th><th>Vendor</th><th>Exposure</th><th>Status</th></tr>{rows}</table>
<h3 class="warn">UNCHECKED: could not read, not "no change"</h3><ul>{unchecked}</ul>
<p><a href="/files/{run_id}/impact.xlsx">Download Excel</a> &middot;
<a href="/files/{run_id}/markup.pdf">Download marked-up PDF</a> &middot;
<a href="/">Run another</a> &middot;
<form method="post" action="/delete/{run_id}" style="display:inline"><button type="submit">Delete this run now</button></form></p>"""
    return page(body)


@app.post("/delete/<run_id>")
def delete_run(run_id):
    if not run_id.isalnum():
        abort(404)
    shutil.rmtree(os.path.join(WORK, run_id), ignore_errors=True)
    return page("<p class='ok'>Deleted. Working files for this run are gone.</p><p><a href='/'>Back</a></p>")


@app.get("/files/<run_id>/<name>")
def files(run_id, name):
    if not run_id.isalnum() or name not in ("impact.xlsx", "markup.pdf"):
        abort(404)
    return send_from_directory(os.path.join(WORK, run_id), name, as_attachment=True)


if __name__ == "__main__":
    # 127.0.0.1 only: not reachable from other computers on the network.
    app.run(host="127.0.0.1", port=5057, debug=False)
