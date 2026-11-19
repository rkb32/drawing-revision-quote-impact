"""Customer change-order draft from a run. Shows what each change costs the shop to absorb.

The customer price is NOT known to the tool. Each line shows the vendor cost basis and a blank
field for the shop's markup. Nothing is sent. The shop reviews and edits before use.
"""


def build(summary, part_no, shop_name="[shop]", customer="[customer]", markup_pct=None):
    lines = [f"# Change order draft (NOT SENT) for part {part_no}",
             f"From: {shop_name}    To: {customer}", ""]
    priced = [r for r in summary["rows"] if r.get("exposure_usd") is not None and r["vendor"] != "-"]
    cost_by_vendor = summary["priced_exposure_by_vendor_usd"]
    for ch in summary["changes_with_location"]:
        rows = [r for r in summary["rows"] if r["field"] == ch["field"]]
        action = rows[0]["action"] if rows else "review"
        lines.append(f"- {ch['field']}: {ch['old']} -> {ch['new']}. Action: {action}.")
        lines.append(f"  Requires customer approval before work continues.")
    lines += ["", "Cost basis (vendor exposure for the requote lines, one vendor at a time):"]
    for v, amt in cost_by_vendor.items():
        lines.append(f"  {v}: ${amt:.2f}")
    if markup_pct is not None:
        lines.append(f"Markup applied: {markup_pct}%")
    lines += ["", "Customer price change: [shop to enter]", "",
              "Unpriced items need engineering or material quotes before a price can be set:"]
    for r in summary["rows"]:
        if r["status"].startswith("unpriced"):
            lines.append(f"  - {r['field']}: {r['status']}")
    lines += ["", "[shop signature]"]
    return "\n".join(lines) + "\n"
