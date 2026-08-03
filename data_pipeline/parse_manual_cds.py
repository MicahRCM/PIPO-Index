"""Parse manually-downloaded CDS files (human-in-the-loop tier).

You download the wall-blocked CDS files (Cloudflare/Box) into data/cds_manual/,
naming each by UNITID (e.g. 219709.pdf, 243780.xlsx). This script parses each
with the SAME extractor used by the free/browser tiers, appends new rows to
data/cds_data.csv, and drops them from data/cds_blocked.csv.

Filename must start with the UNITID. Supported: .pdf .xlsx .xls .html
Run:  python3 data_pipeline/parse_manual_cds.py [--dry-run]
"""
import argparse, csv, glob, os, re, sys
import fetch_cds as fc

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL = os.path.join(REPO, "data", "cds_manual")
DATA = os.path.join(REPO, "data", "cds_data.csv")
BLOCKED = os.path.join(REPO, "data", "cds_blocked.csv")
FIELDS = ["unitid", "name", "cds_year", "cds_url", "hs_gpa", "pct_top10_hs",
          "pct_need_met", "merit_aid_total", "need_aid_total", "avg_aid_package",
          "pct_commuter", "pct_demonstrated_need"]


def load_manifest():
    m = {}
    path = os.path.join(MANUAL, "_manifest.csv")
    if os.path.exists(path):
        for r in csv.DictReader(open(path)):
            m[r["unitid"]] = r
    return m


def parse_one(path, url_hint=""):
    """Return (row_dict_or_None, reason). Mirrors fetch_cds --parse-file."""
    low = path.lower()
    if low.endswith((".pdf", ".xlsx", ".xls")):
        if low.endswith(".pdf"):
            # a landing page saved as .pdf isn't a real PDF
            with open(path, "rb") as fh:
                if fh.read(4) != b"%PDF":
                    return None, "not_a_pdf (re-download the actual file)"
            values, fy = fc.parse_pdf_file(path, url_hint)
        else:
            values, fy = fc.xlsx_values(path, url_hint)
        if not values:
            return None, "parse_fail (unreadable/scanned)"
        row, status, reason = fc._assemble_row([(values, fy)])
        if not row:
            return None, reason or "no_cds_values_found"
        return row, "ok"
    # html
    row, status, reason = fc.parse_cds_text(fc.html_to_text(path), url_hint)
    return row, (reason or "ok" if row else "html_parse_fail")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="parse & report, write nothing")
    args = ap.parse_args()

    manifest = load_manifest()
    files = [f for f in glob.glob(os.path.join(MANUAL, "*"))
             if f.lower().endswith((".pdf", ".xlsx", ".xls", ".html"))]
    if not files:
        print(f"No CDS files found in {MANUAL} (drop <unitid>.pdf files there).")
        return

    parsed, skipped = {}, []
    for path in sorted(files):
        base = os.path.basename(path)
        m = re.match(r"(\d+)", base)
        if not m:
            skipped.append((base, "no unitid in filename"))
            continue
        uid = m.group(1)
        meta = manifest.get(uid, {})
        row, reason = parse_one(path, meta.get("url", ""))
        if not row:
            skipped.append((base, reason))
            continue
        out = {k: row.get(k, "") for k in FIELDS}
        out["unitid"] = uid
        out["name"] = meta.get("name", row.get("name", ""))
        if not out.get("cds_url"):
            out["cds_url"] = meta.get("url", "")
        filled = sum(1 for k in FIELDS[4:] if out.get(k) not in ("", None))
        parsed[uid] = out
        print(f"  OK   {uid:>7}  +{filled}v  {out['name'][:42]}")

    for base, reason in skipped:
        print(f"  MISS {base:<22} {reason}")
    print(f"\nParsed {len(parsed)} / {len(files)} files ({len(skipped)} skipped).")

    if args.dry_run or not parsed:
        if args.dry_run:
            print("(dry run — no files written)")
        return

    # append new rows to cds_data.csv (dedup on unitid)
    existing = {r["unitid"] for r in csv.DictReader(open(DATA))}
    new = [u for u in parsed if u not in existing]
    with open(DATA, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        for u in new:
            w.writerow(parsed[u])
    # remove parsed unitids from cds_blocked.csv
    brows = list(csv.DictReader(open(BLOCKED)))
    bf = list(brows[0].keys()) if brows else ["unitid", "name", "attempted_url", "reason"]
    kept = [r for r in brows if r["unitid"] not in parsed]
    removed = len(brows) - len(kept)
    with open(BLOCKED, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=bf)
        w.writeheader(); w.writerows(kept)
    print(f"Appended {len(new)} new rows to cds_data.csv; removed {removed} from cds_blocked.csv.")
    dupes = [u for u in parsed if u in existing]
    if dupes:
        print(f"({len(dupes)} already in cds_data.csv, left unchanged: {', '.join(dupes)})")


if __name__ == "__main__":
    main()
