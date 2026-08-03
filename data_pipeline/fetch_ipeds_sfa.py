"""Pull IPEDS Student Financial Aid grant variables for every institution.

Fills two variables the government DOES have but we hadn't extracted — giving
near-universal coverage where CDS only gave us ~408 schools:
  - avg_grant_aid           average grant/scholarship $ among recipients (all UG)
  - pct_receiving_grant_aid % of undergrads receiving grant/scholarship aid

Source: Urban Institute Education Data API, ipeds/sfa-all-undergraduates,
type_of_aid=3 (grant or scholarship aid). Years 2008-2021 (API coverage).

Usage:
  python3 data_pipeline/fetch_ipeds_sfa.py --test        # 5 schools, prints
  python3 data_pipeline/fetch_ipeds_sfa.py               # full -> data/ipeds_sfa_grants.csv
"""
import argparse, csv, json, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE = "https://educationdata.urban.org/api/v1/college-university/ipeds"
REPO = Path(__file__).resolve().parent.parent
MASTER = REPO / "data" / "institutions_master.csv"
OUT = REPO / "data" / "ipeds_sfa_grants.csv"
YEARS = range(2008, 2022)          # 2008-2021 inclusive
BATCH = 200
SLEEP = 0.3
RETRIES = 4
TIMEOUT = 60


def get_json(url):
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PIPO-Index/sfa-puller"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.load(resp)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            if getattr(e, "code", None) == 404:
                return {"results": []}
            time.sleep(SLEEP * (attempt + 1) * 2)
    return {"results": []}


def load_unitids():
    seen = []
    s = set()
    with MASTER.open() as f:
        for r in csv.DictReader(f):
            u = r.get("unitid")
            if u and u not in s:
                s.add(u); seen.append(int(u))
    return seen


def fetch(ids, years):
    """Yield (unitid, year, avg_grant_aid, pct_receiving_grant_aid)."""
    for year in years:
        for i in range(0, len(ids), BATCH):
            batch = ids[i:i + BATCH]
            url = (f"{BASE}/sfa-all-undergraduates/{year}/?"
                   + urllib.parse.urlencode({"unitid": ",".join(map(str, batch)),
                                             "type_of_aid": 3}))
            for r in get_json(url).get("results", []):
                pct = r.get("percent_of_students")
                amt = r.get("average_amount")
                if pct is None and amt is None:
                    continue
                yield (r["unitid"], year,
                       amt if amt is not None else "",
                       round(pct * 100, 1) if isinstance(pct, (int, float)) and pct >= 0 else "")
            time.sleep(SLEEP)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    if args.test:
        ids = [186131, 139959, 100858, 190567, 243780]  # Princeton, UGA, Auburn, CCNY, Purdue
        print("unitid   year  avg_grant  pct_recv")
        for row in fetch(ids, [2015, 2020]):
            print(f"{row[0]:<8} {row[1]}  {str(row[2]):>9}  {row[3]}")
        return

    ids = load_unitids()
    print(f"pulling SFA grant aid for {len(ids)} institutions x {len(list(YEARS))} years...",
          file=sys.stderr)
    n = 0
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unitid", "year", "avg_grant_aid", "pct_receiving_grant_aid"])
        for row in fetch(ids, YEARS):
            w.writerow(row); n += 1
    print(f"wrote {n} rows -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
