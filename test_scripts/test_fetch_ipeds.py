"""
One-off smoke test for data_pipeline/fetch_ipeds.py.

Runs a tiny live pull (UAB 100663 + 2 peers, a few years) against the open
Urban Institute API and asserts that real, sane values land for each series.
Validates UAB 2020 net-price bands against the figures documented in
data_pipeline/variable_sources.md.

Run:  python3 test_scripts/test_fetch_ipeds.py
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "fetch_ipeds", ROOT / "data_pipeline" / "fetch_ipeds.py")
fp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp)

UAB = 100663
IDS = [UAB, 100751, 243744]


def collect(fn, years):
    return list(fn(IDS, years))


def get(rows, uid, var):
    return [v for (u, y, k, v) in rows if u == uid and k == var]


def main():
    failures = []

    def check(cond, msg):
        print(("PASS" if cond else "FAIL"), msg)
        if not cond:
            failures.append(msg)

    ret = collect(fp.fetch_retention, [2018, 2020])
    v = get(ret, UAB, "retention_ft")
    check(v and all(0.5 <= x <= 1 for x in v), f"retention_ft UAB = {v}")

    grad = collect(fp.fetch_grad, [2018])
    v = get(grad, UAB, "grad_rate_6yr")
    check(v and abs(v[0] - 0.634) < 0.001, f"grad_rate_6yr UAB 2018 = {v} (exp ~0.634)")

    pell = collect(fp.fetch_pell_grad, [2016])
    p = get(pell, UAB, "grad_rate_6yr_pell")
    np = get(pell, UAB, "grad_rate_6yr_nonpell")
    check(p and 0 < p[0] < 1, f"grad_rate_6yr_pell UAB 2016 = {p}")
    check(np and np[0] > p[0], f"nonpell ({np}) > pell ({p})")

    enr = collect(fp.fetch_enrollment, [2018])
    pt = get(enr, UAB, "pct_part_time")
    intl = get(enr, UAB, "pct_international")
    white = get(enr, UAB, "pct_white")
    check(pt and 0 < pt[0] < 0.5, f"pct_part_time UAB 2018 = {pt}")
    check(intl and abs(intl[0] - 0.0213) < 0.005, f"pct_international UAB 2018 = {intl}")
    check(white and 0.5 < white[0] < 0.62, f"pct_white UAB 2018 = {white}")

    netp = collect(fp.fetch_netprice, [2020])
    expected = {"net_price_0_30k": 13862, "net_price_30_48k": 15370,
                "net_price_48_75k": 16847, "net_price_75_110k": 18230,
                "net_price_110k_plus": 20054}
    for col, exp in expected.items():
        v = get(netp, UAB, col)
        check(v and v[0] == exp, f"{col} UAB 2020 = {v} (doc'd {exp})")

    pell_pct = collect(fp.fetch_pctpell, [2020])
    v = get(pell_pct, UAB, "pct_pell")
    check(v and 0 < v[0] < 1, f"pct_pell UAB 2020 = {v}")

    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
