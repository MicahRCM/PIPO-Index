"""Regenerate web/data/university_data.json (the new Vercel site's value-added
source) from the 2024 rerun spreadsheet `valuedaddedindex.xlsx`.

Downstream: after this, run `python3 data_pipeline/build_app_dataset.py` to
rebuild web/data/institutions.json (which the Next.js tools actually read).

Field map (target schema verified against the current file):
  Name           <- Name
  VA Retention   <- VA Retention  * 100   (percent points, 1 dp)
  VA Graduation  <- VA Graduation * 100
  Graduation Rate<- Graduation Rate * 100
  Retention Rate <- Retention Rate * 100
  US News Rank   <- US News Rank
  UNITID         <- ipedsid
  nationalu      <- nationalu
  state          <- state        (2-letter, kept as-is)
  region         <- region       (full name)
  pubpriv        <- pubpriv       ("public"->1, "private"->2)
  VAdistance     <- SUPPLIED SEPARATELY (not in the four tool spreadsheets)

VAdistance source (first that exists):
  1. a "VAdistance" column inside valuedaddedindex.xlsx, OR
  2. data/2024 tool data/vadistance.csv  with columns: ipedsid,VAdistance
Run with --allow-missing to preview the file with VAdistance=null.
"""
import argparse, csv, json, openpyxl
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TD = REPO / "data" / "2024 tool data"
INDEX = TD / "valuedaddedindex.xlsx"
VADIST_CSV = TD / "vadistance.csv"
OUT = REPO / "web" / "data" / "university_data.json"

VADIST_ALIASES = ["VAdistance", "VA distance", "VADistance", "VA Distance", "VAdist"]


def pp(v):
    return round(float(v) * 100, 1) if v is not None else None


def load_vadistance(H, rows):
    # 1) column inside the index xlsx
    for a in VADIST_ALIASES:
        if a in H:
            return {int(r[H["ipedsid"]]): (float(r[H[a]]) if r[H[a]] is not None else None)
                    for r in rows}, f"column '{a}' in valuedaddedindex.xlsx"
    # 2) separate csv
    if VADIST_CSV.exists():
        m = {}
        for r in csv.DictReader(VADIST_CSV.open()):
            uid = r.get("ipedsid") or r.get("UNITID") or r.get("unitid")
            vd = r.get("VAdistance") or r.get("vadistance") or r.get("VA distance")
            if uid and vd not in (None, ""):
                m[int(float(uid))] = float(vd)
        return m, f"{VADIST_CSV.name}"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-missing", action="store_true",
                    help="write with VAdistance=null where unavailable (preview only)")
    args = ap.parse_args()

    ws = openpyxl.load_workbook(INDEX, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    H = {c: i for i, c in enumerate(rows[0])}
    data = [r for r in rows[1:] if r[H["ipedsid"]] is not None]

    vadist, source = load_vadistance(H, data)
    if vadist is None and not args.allow_missing:
        raise SystemExit(
            "VAdistance not found. Provide it either as a 'VAdistance' column in "
            f"valuedaddedindex.xlsx, or as {VADIST_CSV} (columns: ipedsid,VAdistance). "
            "Or run with --allow-missing to preview with nulls.")

    recs, missing = [], 0
    for r in data:
        uid = int(r[H["ipedsid"]])
        vd = (vadist or {}).get(uid)
        if vd is None:
            missing += 1
        recs.append({
            "Name": r[H["Name"]],
            "VA Retention": pp(r[H["VA Retention"]]),
            "VA Graduation": pp(r[H["VA Graduation"]]),
            "Graduation Rate": pp(r[H["Graduation Rate"]]),
            "Retention Rate": pp(r[H["Retention Rate"]]),
            "US News Rank": int(r[H["US News Rank"]]) if r[H["US News Rank"]] is not None else None,
            # stored as percentage points like the other VA fields (source is a
            # decimal, e.g. 0.2313 -> 23.1). The site's charts auto-scale but
            # assume spans > 1, so decimals must not be passed through raw.
            "VAdistance": pp(vd) if vd is not None else None,
            "UNITID": uid,
            "nationalu": int(r[H["nationalu"]]),
            "state": (r[H["state"]] or "").strip(),
            "region": (r[H["region"]] or "").strip(),
            "pubpriv": 1 if str(r[H["pubpriv"]]).lower() == "public" else 2,
        })

    print(f"records: {len(recs)}  (was 1249)")
    print(f"VAdistance source: {source or 'NONE — nulls'}")
    print(f"VAdistance missing: {missing}/{len(recs)}")
    if missing and not args.allow_missing:
        raise SystemExit(f"{missing} schools have no VAdistance — aborting (use --allow-missing to preview).")

    OUT.write_text(json.dumps(recs, ensure_ascii=False, indent=1))
    print(f"wrote {OUT}")
    print("NEXT: python3 data_pipeline/build_app_dataset.py  -> rebuilds web/data/institutions.json")


if __name__ == "__main__":
    main()
