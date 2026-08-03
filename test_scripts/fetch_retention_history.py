"""
Fetch full-time first-to-second-year retention rate history for every UNITID
present in university_data.json from the College Scorecard API
(https://collegescorecard.ed.gov/data/documentation/). Scorecard sources its
retention data from IPEDS but is published with less lag, so it has more
recent years than the Urban Institute IPEDS proxy.

Writes two files:
  - assets/retention_history.json    : compact JSON
  - assets/retention_history.js      : same payload wrapped as
                                       `window.RETENTION_DATA = {...}`
                                       so Retention.html works under file://

Shape:
{
  "years": [2016, ..., 2024],
  "universities": {
      "<UNITID>": {"name": "...", "rates": [82.0, ...]}   // null for missing
  }
}

API rate limits: data.gov DEMO_KEY allows ~30 req/hr / 50 req/day. With
batched UNITIDs and pagination, the full pull is ~12-15 requests. Set the
COLLEGE_SCORECARD_API_KEY env var to use a personal key
(free signup: https://api.data.gov/signup/).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNI_DATA = ROOT / "university_data.json"
OUT_FILE = ROOT / "assets" / "retention_history.json"
OUT_JS = ROOT / "assets" / "retention_history.js"
YEARS = list(range(2016, 2025))   # 2016 through 2024 inclusive
BATCH_SIZE = 20                   # Scorecard returns HTTP 500 above ~22 ids
                                  # when many year-suffixed fields are combined.
PER_PAGE = 100                    # API max
API_KEY = os.environ.get("COLLEGE_SCORECARD_API_KEY", "DEMO_KEY")
BASE = "https://api.data.gov/ed/collegescorecard/v1/schools"


def build_url(ids: list[str], page: int) -> str:
    fields = ["id"] + [
        f"{y}.student.retention_rate.four_year.full_time" for y in YEARS
    ]
    params = {
        "id": ",".join(ids),
        "fields": ",".join(fields),
        "per_page": str(PER_PAGE),
        "page": str(page),
        "api_key": API_KEY,
    }
    return BASE + "?" + urllib.parse.urlencode(params)


def fetch(ids: list[str]) -> dict[int, dict[int, float]]:
    """Return {unitid: {year: pct}} for the given UNITID batch."""
    out: dict[int, dict[int, float]] = {}
    page = 0
    while True:
        url = build_url(ids, page)
        print(f"  page {page}: GET .../schools?id=<{len(ids)} ids>"
              f"&page={page}")
        try:
            with urllib.request.urlopen(url, timeout=90) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code} on page {page}: {e.read()[:200]!r}",
                  file=sys.stderr)
            raise
        for row in payload.get("results", []):
            uid = int(row["id"])
            rates: dict[int, float] = {}
            for y in YEARS:
                v = row.get(f"{y}.student.retention_rate.four_year.full_time")
                if v is None or v < 0:
                    continue
                rates[y] = round(v * 100, 1)
            if rates:
                out[uid] = rates
        total = payload.get("metadata", {}).get("total", 0)
        if (page + 1) * PER_PAGE >= total:
            break
        page += 1
        time.sleep(0.2)
    return out


def main() -> int:
    if not UNI_DATA.exists():
        print(f"missing {UNI_DATA}", file=sys.stderr)
        return 1
    with UNI_DATA.open() as f:
        unis = json.load(f)

    unitids = [str(u["UNITID"]) for u in unis if u.get("UNITID") is not None]
    print(f"Fetching {len(unitids)} universities in batches of {BATCH_SIZE}, "
          f"years {YEARS[0]}-{YEARS[-1]}...")

    all_rates: dict[int, dict[int, float]] = {}
    for i in range(0, len(unitids), BATCH_SIZE):
        batch = unitids[i:i + BATCH_SIZE]
        print(f"Batch {i // BATCH_SIZE + 1} "
              f"({i + 1}-{i + len(batch)})...")
        all_rates.update(fetch(batch))

    print(f"Collected data for {len(all_rates)} universities")

    out = {"years": YEARS, "universities": {}}
    matched = 0
    for u in unis:
        unitid = u.get("UNITID")
        if unitid is None:
            continue
        rates_map = all_rates.get(int(unitid), {})
        rates = [rates_map.get(y) for y in YEARS]
        if any(r is not None for r in rates):
            matched += 1
        out["universities"][str(unitid)] = {
            "name": u.get("Name"),
            "rates": rates,
        }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w") as f:
        json.dump(out, f, separators=(",", ":"))

    with OUT_JS.open("w") as f:
        f.write("window.RETENTION_DATA = ")
        json.dump(out, f, separators=(",", ":"))
        f.write(";\n")

    total = len(out["universities"])
    print(f"Wrote {OUT_FILE.relative_to(ROOT)} and "
          f"{OUT_JS.relative_to(ROOT)}: "
          f"{matched}/{total} unis have at least one data point")
    return 0


if __name__ == "__main__":
    sys.exit(main())
