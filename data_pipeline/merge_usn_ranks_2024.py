"""Merge the real US-News 2026-edition ranks into the master at year 2024.

Source: data/usn_categories.csv — the public US-News rankings-listing scrape,
validated 100% exact against Alix's confidential internal file, so these are the
genuine published 2026-edition ranks (with real ties), carrying IPEDS unitid.
2026 edition == fall-2024 cohort (edition - 2), so they land at year 2024,
consistent with the Compass layer.

Actions at year 2024, keyed on unitid:
  - overwrite `usn_rank` with the 2026-edition rank (upgrades the stale/partial
    Reiter-sourced 2024 ranks; also fills the ~1,132 schools that had none)
  - add `usn_id`            (US-News school id)
  - add `usn_category_all`  (all-10-category label; existing `usn_category` kept)

Non-destructive elsewhere: only year-2024 rows are touched; no other column or
year changes. Backs up to data/institutions_master.pre_ranks2024.csv.
"""
import argparse, csv, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MASTER = REPO / "data" / "institutions_master.csv"
CATS = REPO / "data" / "usn_categories.csv"
BACKUP = REPO / "data" / "institutions_master.pre_ranks2024.csv"
YEAR = "2024"
NEWCOLS = ["usn_id", "usn_category_all"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # unitid -> (rank, usn_id, category)
    ref = {}
    for r in csv.DictReader(CATS.open()):
        uid, rk = r["unitid"].strip(), r["rank"].strip()
        if uid and rk:
            ref[uid] = (rk, r["usn_id"].strip(), r["category"].strip())

    with MASTER.open() as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        rows = list(rd)
    outcols = cols + [c for c in NEWCOLS if c not in cols]

    overwritten = added = unchanged = 0
    examples = []
    for r in rows:
        for c in NEWCOLS:
            r.setdefault(c, "")
        if r["year"] == YEAR and r["unitid"] in ref:
            rk, uid, cat = ref[r["unitid"]]
            old = r.get("usn_rank", "").strip()
            if old and old != rk:
                overwritten += 1
                if len(examples) < 8:
                    examples.append((r.get("name", "")[:26], old, rk))
            elif not old:
                added += 1
            else:
                unchanged += 1
            r["usn_rank"] = rk
            r["usn_id"] = uid
            r["usn_category_all"] = cat

    filled = overwritten + added + unchanged
    print(f"=== USN 2026-edition ranks -> master year {YEAR} ({'DRY RUN' if args.dry_run else 'WRITING'}) ===")
    print(f"schools matched at {YEAR}: {filled}  (of {len(ref)} ranked in usn_categories)")
    print(f"  usn_rank overwritten (changed value): {overwritten}")
    print(f"  usn_rank newly added (was blank):     {added}")
    print(f"  usn_rank unchanged (already correct):  {unchanged}")
    print(f"new columns: {NEWCOLS}")
    print("sample rank changes (name: old -> new):")
    for nm, o, n in examples:
        print(f"    {nm:26} {o} -> {n}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return

    shutil.copy2(MASTER, BACKUP)
    with MASTER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=outcols)
        w.writeheader()
        w.writerows(rows)
    print(f"\nbacked up -> {BACKUP}")
    print(f"wrote {MASTER}  ({len(cols)} -> {len(outcols)} cols)")


if __name__ == "__main__":
    main()
