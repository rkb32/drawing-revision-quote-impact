"""Entity-level DXF diff: compares the drawing's model-space entities, not pixels.
Entities are matched by a signature (type, layer, geometry rounded to 0.001 units).
Only entities present on one side are reported as added or removed. A moved entity shows as one removed and one added."""
from collections import Counter

import ezdxf

PREC = 3


def _r(v):
    return round(float(v), PREC)


def _sig(e):
    t = e.dxftype()
    layer = e.dxf.layer
    if t == "LINE":
        pts = (tuple(map(_r, e.dxf.start)), tuple(map(_r, e.dxf.end)))
    elif t == "CIRCLE":
        pts = (tuple(map(_r, e.dxf.center)), _r(e.dxf.radius))
    elif t == "ARC":
        pts = (tuple(map(_r, e.dxf.center)), _r(e.dxf.radius), _r(e.dxf.start_angle), _r(e.dxf.end_angle))
    elif t in ("TEXT", "MTEXT"):
        text = e.dxf.text if t == "TEXT" else e.text
        pts = (text.strip(), tuple(map(_r, e.dxf.insert)))
    elif t == "LWPOLYLINE":
        pts = tuple(tuple(_r(c) for c in p[:2]) for p in e.get_points())
    else:
        pts = ("unsupported",)
    return (t, layer, pts)


def entities(path):
    """Counter of entity signatures in model space."""
    return Counter(_sig(e) for e in ezdxf.readfile(path).modelspace())


def diff(old_path, new_path):
    """Returns (added, removed, unsupported_old, unsupported_new).
    added/removed: list of ((type, layer, geometry), count). unsupported_*: entities of a type not compared, per file."""
    a, b = entities(old_path), entities(new_path)
    added = [(k, n) for k, n in (b - a).items()]
    removed = [(k, n) for k, n in (a - b).items()]
    unsupported_old = sum(n for k, n in a.items() if k[2] == ("unsupported",))
    unsupported_new = sum(n for k, n in b.items() if k[2] == ("unsupported",))
    return added, removed, unsupported_old, unsupported_new
