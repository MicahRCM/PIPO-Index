"""Inject the scraped College Navigator average net price into the app dataset.

Reads data/navigator_avg_net_price.csv (from scrape_navigator_avg_netprice.py)
and writes metrics['avg_net_price_nav'] onto each matching record in
web/data/institutions.json. Idempotent: re-running overwrites the field.

The app (web/src/lib/data.ts) derives `avg_net_price` preferring this field, so
both VAC ("Average" band) and CAS ("Average" column) show the correct,
enrollment-weighted figure that matches Navigator.
"""
import csv, json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INST = REPO / "web" / "data" / "institutions.json"
CSV  = REPO / "data" / "navigator_avg_net_price.csv"

def main():
    nav = {}
    with CSV.open() as f:
        for r in csv.DictReader(f):
            v = r["nav_avg_net_price"]
            if v not in ("", None):
                nav[str(r["unitid"])] = int(float(v))
    data = json.load(INST.open())
    records = data["data"] if isinstance(data, dict) and "data" in data else data
    set_n = miss = 0
    for rec in records:
        uid = str(rec.get("unitid"))
        m = rec.setdefault("metrics", {})
        if uid in nav:
            m["avg_net_price_nav"] = nav[uid]
            set_n += 1
        else:
            # only counts as a miss if the school actually has band data
            if any(m.get(b) is not None for b in
                   ["net_price_0_30k","net_price_30_48k","net_price_48_75k",
                    "net_price_75_110k","net_price_110k_plus"]):
                miss += 1
    with INST.open("w") as f:
        json.dump(records if not (isinstance(data,dict) and "data" in data) else data,
                  f, ensure_ascii=False, indent=1)
    print(f"set avg_net_price_nav on {set_n} records; {miss} band-having records had no Navigator avg")

if __name__ == "__main__":
    main()
