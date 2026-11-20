"""Streamlit version for Streamlit Community Cloud (free).

Files are uploaded to a temporary folder that is deleted at the end of the run.
Nothing is written to a persistent location, and learning/decision logging is not used.
Run locally:  streamlit run streamlit_app.py
"""
import io
import os
import shutil
import tempfile
import zipfile

import streamlit as st

import dxf_diff
import impact

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(HERE, "samples")
POLICY = ("Your files are sent over an encrypted (HTTPS) connection to the server, processed, "
          "and deleted as soon as your results are returned. We do not keep, view, or share them. "
          "This is a free early tool with no security certification. If your contract forbids sending "
          "a customer's drawings to third parties, do not upload them: use the sample files, or run "
          "the tool on your own computer (instructions are in the GitHub README).")

st.set_page_config(page_title="Revision impact", layout="centered")
st.title("Drawing revision impact")
st.write("Upload the old and new drawing, the BOM and the quote sheet. "
         "Get back an Excel sheet, a marked-up PDF and a change-order draft.")
st.warning(POLICY)

with st.expander("How it works and how to read the results"):
    st.graphviz_chart("""
digraph G {
  rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#fafaf7", fontname="Helvetica"];
  up [label="1. Upload\nold + new PDF, BOM, quotes"];
  read [label="2. Read fields\n(stud length, material, holes ...)"];
  diff [label="3. Diff changes\nmatch BOM and quote lines"];
  out [label="4. Results\nexposure per vendor\ncost and heat-cert checks"];
  unk [label="UNCHECKED\nnot read on one side:\nNOT 'no change'", fillcolor="#fff7e6"];
  up -> read -> diff -> out;
  read -> unk [style=dashed];
}
""")
    st.markdown(
        "- **Changes:** a field read on both drawings that differs.\n"
        "- **Exposure:** unit price x BOM quantity, one vendor at a time. Vendors are never added together.\n"
        "- **UNCHECKED:** a field we could not read on one side. It is never reported as 'no change'.\n"
        "- **Warning:** text differs outside the field rules. Review those sheets by hand.\n"
        "- **Cost and heat certs:** only when you supply a price table or cert file.")


def sheet_pngs(old_pdf, new_pdf, changes):
    """Old and new first sheets as PNG with a red box on each changed value."""
    import pymupdf as _pm

    def render(path, key):
        doc = _pm.open(path)
        for c in changes:
            loc = c.get(key)
            if not loc:
                continue
            idx = min(max(loc["page"] - 1, 0), len(doc) - 1)
            x, y = loc["x"], loc["y"]
            doc[idx].draw_rect(_pm.Rect(x - 4, y - 4, x + 90, y + 14), color=(0.85, 0.1, 0.1), width=2)
        return doc[0].get_pixmap(dpi=110).tobytes("png")

    return render(old_pdf, "loc_old"), render(new_pdf, "loc_new")


def run_on(paths, part):
    """Returns (summary dict, zip bytes, overlay PNG bytes)."""
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
        summary += ["", "Policy: " + POLICY]
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("summary.txt", "\n".join(summary) + "\n")
            for name in ("impact.xlsx", "markup.pdf", "overlay.png", "change_order_draft.md", "drafts.md", "summary.json",
                         "change_report.pdf", "change_report.csv"):
                p = os.path.join(out, name)
                if os.path.exists(p):
                    z.write(p, name)
        with open(os.path.join(out, "overlay.png"), "rb") as fh:
            overlay = fh.read()
        s["_sheets"] = sheet_pngs(paths["old"], paths["new"], s["changes_with_location"])
        return s, buf.getvalue(), overlay
    finally:
        shutil.rmtree(work, ignore_errors=True)


def show_visual(s, overlay):
    """Visual diff first: the sheets side by side with changes boxed, then the overlay."""
    st.subheader("Visual diff")
    if "_sheets" in s:
        old_png, new_png = s["_sheets"]
        c1, c2 = st.columns(2)
        c1.image(old_png, caption="Old drawing (red box = changed value)")
        c2.image(new_png, caption="New drawing (red box = changed value)")
    st.image(overlay, caption="Overlay. Red: only on old drawing. Blue: only on new drawing. Black: on both.")


def show_extra(s, overlay):
    """Items the CLI prints or writes to summary.json that the first version did not show."""
    st.subheader("Stud length cost (material only, from your price table)")
    st.dataframe(s["cost_delta"]) if s["cost_delta"] else st.write("No stud length change.")
    st.subheader("Heat certs (material changes only)")
    hc = s["heat_cert"]
    if isinstance(hc, str):
        st.write(hc)
    elif hc:
        st.dataframe(hc)
    else:
        st.write("No material change, so no cert check.")

    if s.get("uncovered_text_warning"):
        st.warning(s["uncovered_text_warning"])
    st.subheader("Revision check (quote vs new drawing revision)")
    if s["rev_guard"]:
        st.dataframe(s["rev_guard"])
        st.caption("A quote with no rev column is flagged, not passed: add a rev column to confirm the revision.")
    else:
        st.write("No quote lines for this part.")

    st.subheader("Change locations")
    locs = [{"field": c["field"], "old": c["old"], "new": c["new"], "location on new drawing": c["loc_new"]}
            for c in s["changes_with_location"]]
    st.dataframe(locs) if locs else st.write("No changes found.")

    st.subheader("Quote expiry")
    st.write(s["expiry_flags"] or "No expiry problems for this part.")

    st.subheader("Revision block cross-check")
    st.write(s["revision_block_cross_check"] or "Revision block agrees with the detected changes.")

    st.subheader("Text changes outside the priced fields")
    st.write(f"Words only on old drawing: {len(s['text_words_removed'])}. "
             f"Words only on new drawing: {len(s['text_words_added'])}.")
    if s["text_words_added"] or s["text_words_removed"]:
        st.dataframe([{"side": "old only", **w} for w in s["text_words_removed"][:200]]
                     + [{"side": "new only", **w} for w in s["text_words_added"][:200]])
        st.caption("First 200 of each shown here. The full list is in summary.json in the zip.")

    st.subheader("Drawing overlay details")
    st.write(f"Regions highlighted on the marked-up PDF: {s['raster_boxes']}. "
             f"Alignment shift: {s['raster_shift_px']} px.")


def run_dxf(old_bytes, new_bytes):
    """Entity-level DXF compare. Only for CAD files; PDFs use the main run."""
    work = tempfile.mkdtemp(prefix="revimpact_dxf_")
    try:
        op, np_ = os.path.join(work, "old.dxf"), os.path.join(work, "new.dxf")
        with open(op, "wb") as fh:
            fh.write(old_bytes)
        with open(np_, "wb") as fh:
            fh.write(new_bytes)
        return dxf_diff.diff(op, np_)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _clear_result():
    """Any input change makes the stored result stale: drop it so no old numbers stay on screen."""
    st.session_state.pop("result", None)
    st.session_state.pop("result_source", None)


def render_results(res):
    """Draws a finished run. Called from session state, so results survive reruns (e.g. download clicks)."""
    s, zbytes, overlay, dxf_out = res["s"], res["zbytes"], res["overlay"], res["dxf"]
    st.success(f"Done. {s['changes']} change(s), {s['unpriced_rows']} unpriced row(s).")
    vendors = s["priced_exposure_by_vendor_usd"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Changes", s["changes"])
    c2.metric("Unpriced rows", s["unpriced_rows"])
    c3.metric("UNCHECKED fields", len(s["unchecked_fields"]))
    c4.metric("Vendors to requote", len(vendors))
    st.write("Requote needed: " + (", ".join(vendors) if vendors else "none with a priced change"))

    issues = []
    for u in s["unchecked_fields"]:
        issues.append(f"UNCHECKED {u['field']}: rev A {u['rev_A']}, rev B {u['rev_B']}. Read it off the drawing.")
    if s.get("uncovered_text_warning"):
        issues.append(s["uncovered_text_warning"])
    for r in s["rows"]:
        if str(r.get("status", "")).startswith("unpriced"):
            issues.append(f"Unpriced {r['field']} ({r.get('vendor') or 'no vendor'}): {r['status']}")
    for g in s["rev_guard"]:
        issues.append(f"Revision check {g['vendor']}: {g['status']} ({g['detail']})")
    st.subheader("Needs your action")
    if issues:
        for item in issues:
            st.warning(item)
    else:
        st.success("Nothing needs action.")

    show_visual(s, overlay)
    st.subheader("Priced exposure (one vendor at a time, not added together)")
    for v, a in vendors.items():
        st.write(f"{v}: ${a:.2f}")
    st.subheader("Changes")
    st.dataframe([{k: r[k] for k in ("field", "old", "new", "action", "vendor", "exposure_usd", "status")}
                  for r in s["rows"]])
    st.subheader("UNCHECKED (could not read, NOT 'no change')")
    st.write(s["unchecked_fields"] or "None. Every field was read on both drawings.")
    show_extra(s, overlay)
    if dxf_out is not None:
        added, removed, u_old, u_new = dxf_out
        st.subheader("CAD entity diff (DXF)")
        st.write(f"Entities only in new file: {sum(n for _, n in added)}. "
                 f"Only in old file: {sum(n for _, n in removed)}. "
                 f"Entity types not compared: old {u_old}, new {u_new}.")
        if added or removed:
            st.dataframe([{"side": "new only", "type": k[0], "layer": k[1], "count": n} for k, n in added]
                         + [{"side": "old only", "type": k[0], "layer": k[1], "count": n} for k, n in removed])
        st.caption("A moved entity shows as one removed and one added.")
    st.subheader("Revision history for this part")
    runs = res.get("runs") or []
    st.caption("Exposure figures are quote prices. Keep this file with the part's job folder; it is not stored on the server.")
    st.dataframe([{"when": r["created"], "old": r.get("old_rev"), "new": r.get("new_rev"),
                   "changed fields": ", ".join(r["changes"]) or "none",
                   "exposure by vendor": str(r["exposure_by_vendor"])} for r in runs])
    if res.get("history_text"):
        st.download_button("Download updated history file (JSON)", res["history_text"],
                           f"history_{res.get('part', 'part')}.json", "application/json")
    st.download_button("Download results (zip)", zbytes, "revision_impact_results.zip", "application/zip")


tab_up, tab_sample = st.tabs(["Run on my files", "Try with sample files"])

with tab_up:
    old = st.file_uploader("Old drawing (PDF)", type=["pdf"], on_change=_clear_result)
    new = st.file_uploader("New drawing (PDF)", type=["pdf"], on_change=_clear_result)
    bom = st.file_uploader("BOM (CSV or XLSX)", type=["csv", "xlsx"], on_change=_clear_result)
    quotes = st.file_uploader("Quote sheet (CSV or XLSX)", type=["csv", "xlsx"], on_change=_clear_result)
    prices_up = st.file_uploader("Optional: price table (CSV, for stud length cost)", type=["csv"], on_change=_clear_result)
    certs_up = st.file_uploader("Optional: heat certs (CSV)", type=["csv"], on_change=_clear_result)
    hist_up = st.file_uploader("Optional: revision history file (JSON from a previous run)", type=["json"], on_change=_clear_result)
    part = st.text_input("Part number to price", value="1234-STD", on_change=_clear_result)
    old_dxf = st.file_uploader("Optional: old CAD file (DXF)", type=["dxf"], on_change=_clear_result)
    new_dxf = st.file_uploader("Optional: new CAD file (DXF)", type=["dxf"], on_change=_clear_result)
    if st.button("Run on my files", disabled=not all([old, new, bom, quotes, part.strip()])):
        work = tempfile.mkdtemp(prefix="revimpact_in_")
        try:
            paths = {}
            for key, f in (("old", old), ("new", new), ("bom", bom), ("quotes", quotes),
                           ("prices", prices_up), ("certs", certs_up)):
                if f is None:
                    continue
                p = os.path.join(work, f"{key}{os.path.splitext(f.name)[1].lower()}")
                with open(p, "wb") as fh:
                    fh.write(f.getbuffer())
                paths[key] = p
            s, zbytes, overlay = run_on(paths, part.strip())
            import history as _hist
            runs = []
            if hist_up is not None:
                try:
                    runs = _hist.load_file(hist_up.getbuffer().tobytes().decode("utf-8"), part.strip())
                except (ValueError, UnicodeDecodeError) as e:
                    st.error(f"History file not used: {e}. Results below are from this run only.")
                    runs = []
            runs = runs + [_hist.to_record(s, part.strip(), s.get("old_rev"))]
            history_text = _hist.dump_file(runs, part.strip())
        finally:
            shutil.rmtree(work, ignore_errors=True)
        dxf_out = None
        if old_dxf and new_dxf:
            dxf_out = run_dxf(old_dxf.getbuffer().tobytes(), new_dxf.getbuffer().tobytes())
        st.session_state["result"] = {"s": s, "zbytes": zbytes, "overlay": overlay, "dxf": dxf_out,
                                      "runs": runs, "history_text": history_text, "part": part.strip()}
        st.session_state["result_source"] = "upload"
    if "result" in st.session_state and st.session_state.get("result_source") == "upload":
        render_results(st.session_state["result"])

with tab_sample:
    st.write("Uses made-up drawings. Nothing is uploaded.")
    if st.button("Run on sample files"):
        paths = {"old": os.path.join(SAMPLES, "drawing_revA.pdf"), "new": os.path.join(SAMPLES, "drawing_revB.pdf"),
                 "bom": os.path.join(SAMPLES, "bom.csv"), "quotes": os.path.join(SAMPLES, "quotes.csv")}
        s, zbytes, overlay = run_on(paths, "1234-STD")
        st.session_state["result"] = {"s": s, "zbytes": zbytes, "overlay": overlay, "dxf": None}
        st.session_state["result_source"] = "sample"
    if "result" in st.session_state and st.session_state.get("result_source") == "sample":
        render_results(st.session_state["result"])
