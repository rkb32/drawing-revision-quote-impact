"""Word-position diff: catches text changes outside the four rule fields (notes, tolerances, rev block).
Words are compared on page text only, after the page offset from raster alignment is applied."""
import pdfplumber


def words_by_page(pdf_path):
    out = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            out.append([(w["text"], round(w["x0"]), round(w["top"])) for w in pg.extract_words()])
    return out


def word_diff(pa, pb, tol=3):
    """Return words only in A (removed) and only in B (added), matched by text and position within tol pt."""
    removed, added = [], []
    A, B = words_by_page(pa), words_by_page(pb)
    for p_idx in range(max(len(A), len(B))):
        wa = A[p_idx] if p_idx < len(A) else []
        wb = B[p_idx] if p_idx < len(B) else []
        matched_b = set()
        for text, x, y in wa:
            hit = None
            for j, (tb, xb, yb) in enumerate(wb):
                if j in matched_b:
                    continue
                if tb == text and abs(xb - x) <= tol and abs(yb - y) <= tol:
                    hit = j
                    break
            if hit is None:
                removed.append({"page": p_idx + 1, "text": text, "x": x, "y": y})
            else:
                matched_b.add(hit)
        for j, (tb, xb, yb) in enumerate(wb):
            if j not in matched_b:
                added.append({"page": p_idx + 1, "text": tb, "x": xb, "y": yb})
    return removed, added
