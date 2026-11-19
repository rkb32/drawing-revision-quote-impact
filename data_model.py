"""Data model for the quote-at-risk checker. Version B triggers (quote expiry, price index)
slot in as new Trigger types without changing these tables."""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Revision:
    drawing_no: str
    rev: str
    issued: date
    source_file: str


@dataclass
class Change:
    drawing_no: str
    from_rev: str
    to_rev: str
    field: str          # stud_len | material | qty | holes | ...
    old_value: str
    new_value: str
    action: str         # Requote | Revalidate | Engineering review | Unchanged


@dataclass
class Material:
    spec: str           # e.g. "A193 B7"


@dataclass
class VendorQuote:
    vendor: str
    bom_line: str
    part_no: str
    unit_price_usd: float
    valid_until: date


@dataclass
class Trigger:          # v1: revision. v2: quote_expiry, price_index_move
    kind: str
    subject: str
    detail: str
    events: list = field(default_factory=list)
