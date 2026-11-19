"""Write one reconfirm DRAFT per vendor, linked to the change rows and quote lines.
Drafts only. Nothing is sent."""
import json
import sys


def build(summary_path, out_path, part_no):
    s = json.load(open(summary_path, encoding="utf-8"))
    rows = [r for r in s["rows"] if r["vendor"] != "-"]
    vendors = sorted({r["vendor"] for r in rows})
    lines = [f"# Reconfirm drafts for part {part_no} (DRAFTS, NOT SENT)", ""]
    for v in vendors:
        vr = [r for r in rows if r["vendor"] == v]
        lines += [f"## To: {v}  (contact: [fill in])", f"Subject: Reconfirm pricing for {part_no}, revised drawing", "",
                  "Hi [name],", "",
                  f"The drawing for {part_no} has a new revision. Please reconfirm your price against it.", ""]
        for r in vr:
            if r["status"] == "priced":
                lines.append(f"- {r['field']}: {r['old']} -> {r['new']}. Requote. Your unit price on file: ${r['unit_usd']} x {r['qty']} = ${r['exposure_usd']}.")
            else:
                lines.append(f"- {r['field']}: {r['old']} -> {r['new']}. {r['action']} (not priced by us; please advise).")
        lines += ["", "Please reply with the revised unit price, lead time, and any cost for the changes above.", "", "Thanks,", "[name]", ""]
    open(out_path, "w", encoding="utf-8").write("\n".join(lines))
    return vendors


if __name__ == "__main__":
    v = build(sys.argv[1], sys.argv[2], sys.argv[3])
    print("drafts for:", v)
