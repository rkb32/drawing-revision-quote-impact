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


def run_on(paths, part):
    work = tempfile.mkdtemp(prefix="revimpact_")
    try:
        out = os.path.join(work, "out")
        s = impact.run(paths["old"], paths["new"], paths["bom"], paths["quotes"], part, out)
        summary = [f"Changes: {s['changes']}", f"Unpriced rows: {s['unpriced_rows']}",
                   "Priced exposure per vendor (not added together):"]
        summary += [f"  {v}: ${a:.2f}" for v, a in s["priced_exposure_by_vendor_usd"].items()]
        summary += ["", "UNCHECKED (could not read on one side, NOT 'no change'):"]
        summary += [f"  {u['field']}: rev A {u['rev_A']}, rev B {u['rev_B']}" for u in s["unchecked_fields"]] or ["  none"]
        summary += ["", "Policy: " + POLICY]
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("summary.txt", "\n".join(summary) + "\n")
            for name in ("impact.xlsx", "markup.pdf", "change_order_draft.md", "drafts.md", "summary.json"):
                p = os.path.join(out, name)
                if os.path.exists(p):
                    z.write(p, name)
        return s, buf.getvalue()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def show_extra(s):
    """Items the CLI prints or writes to summary.json that the first version did not show."""
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

    st.subheader("Drawing overlay check")
    st.write(f"Regions highlighted on the marked-up PDF: {s['raster_boxes']}. "
             f"Alignment shift: {s['raster_shift_px']} px.")


tab_up, tab_sample = st.tabs(["Run on my files", "Try with sample files"])

with tab_up:
    old = st.file_uploader("Old drawing (PDF)", type=["pdf"])
    new = st.file_uploader("New drawing (PDF)", type=["pdf"])
    bom = st.file_uploader("BOM (CSV or XLSX)", type=["csv", "xlsx"])
    quotes = st.file_uploader("Quote sheet (CSV or XLSX)", type=["csv", "xlsx"])
    part = st.text_input("Part number to price", value="1234-STD")
    if st.button("Run on my files", disabled=not all([old, new, bom, quotes, part.strip()])):
        work = tempfile.mkdtemp(prefix="revimpact_in_")
        try:
            paths = {}
            for key, f in (("old", old), ("new", new), ("bom", bom), ("quotes", quotes)):
                p = os.path.join(work, f"{key}{os.path.splitext(f.name)[1].lower()}")
                with open(p, "wb") as fh:
                    fh.write(f.getbuffer())
                paths[key] = p
            s, zbytes = run_on(paths, part.strip())
        finally:
            shutil.rmtree(work, ignore_errors=True)
        st.success(f"Done. {s['changes']} change(s), {s['unpriced_rows']} unpriced row(s).")
        st.subheader("Priced exposure (one vendor at a time, not added together)")
        for v, a in s["priced_exposure_by_vendor_usd"].items():
            st.write(f"{v}: ${a:.2f}")
        st.subheader("Changes")
        st.dataframe([{k: r[k] for k in ("field", "old", "new", "action", "vendor", "exposure_usd", "status")}
                      for r in s["rows"]])
        st.subheader("UNCHECKED (could not read, NOT 'no change')")
        st.write(s["unchecked_fields"] or "None. Every field was read on both drawings.")
        show_extra(s)
        st.download_button("Download results (zip)", zbytes, "revision_impact_results.zip", "application/zip")

with tab_sample:
    st.write("Uses made-up drawings. Nothing is uploaded.")
    if st.button("Run on sample files"):
        paths = {"old": os.path.join(SAMPLES, "drawing_revA.pdf"), "new": os.path.join(SAMPLES, "drawing_revB.pdf"),
                 "bom": os.path.join(SAMPLES, "bom.csv"), "quotes": os.path.join(SAMPLES, "quotes.csv")}
        s, zbytes = run_on(paths, "1234-STD")
        st.success(f"Done. {s['changes']} change(s), {s['unpriced_rows']} unpriced row(s).")
        st.dataframe([{k: r[k] for k in ("field", "old", "new", "action", "vendor", "exposure_usd", "status")}
                      for r in s["rows"]])
        show_extra(s)
        st.download_button("Download sample results (zip)", zbytes, "sample_results.zip", "application/zip")
