"""Draw the raster-diff boxes onto Rev B page image for visual check."""
import cv2, numpy as np, pymupdf
from impact_spike import raster_regions

S = "samples"
boxes = raster_regions(f"{S}/drawing_revA.pdf", f"{S}/drawing_revB.pdf")
doc = pymupdf.open(f"{S}/drawing_revB.pdf")
pix = doc[0].get_pixmap(dpi=100)
img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].copy()
img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
for i, (x, y, w, h) in enumerate(boxes):
    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)
    cv2.putText(img, str(i + 1), (x, max(y - 4, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
cv2.imwrite("out/revB_boxes.png", img)
print("boxes", len(boxes), "saved out/revB_boxes.png")
