#!/usr/bin/env python3
"""
Offline unit test for data_pipeline/fetch_scorecard.py.

Live API testing is blocked right now (DEMO_KEY daily cap exhausted on this IP;
Retry-After ~9h, no personal key available). This test instead feeds a synthetic
Scorecard API response through the real parsing + CSV-writing code paths to
verify:
  - simple field extraction
  - non-Pell grad rate = loan_nopell + noloan_nopell
  - net-price control-suffix branch (picks whichever of _PUB/_PRIV/... is set)
  - null / negative / suppressed values are skipped
  - LONG and WIDE CSVs are written with the expected shape

Run: python3 test_scripts/test_fetch_scorecard.py
"""

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "fetch_scorecard", ROOT / "data_pipeline" / "fetch_scorecard.py"
)
fs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fs)


def _mk_row(uid, year, overrides):
    """Build a flat {`{year}.path`: value} row like the API returns."""
    row = {"id": uid}
    for path, val in overrides.items():
        row[f"{year}.{path}"] = val
    return row


def test_parse_simple_and_skips():
    year = 2018
    row = _mk_row("100663", year, {
        "student.size": 13284,
        "admissions.admission_rate.overall": 0.8854,
        "admissions.sat_scores.75th_percentile.math": 708,
        "student.demographics.race_ethnicity.non_resident_alien": 0.0233,
        "aid.median_debt.completers.overall": None,            # null -> skip
        "student.retention_rate.four_year.full_time": -1,      # negative -> skip
        "cost.tuition.in_state": 8568,
    })
    out = fs.parse_row(row, year)
    assert out["ug_size"] == 13284
    assert out["acceptance_rate"] == 0.8854
    assert out["sat75_math"] == 708
    assert out["pct_international"] == 0.0233
    assert out["tuition_in_state"] == 8568
    assert "median_debt" not in out, "null must be skipped"
    assert "retention_ft_4yr" not in out, "negative must be skipped"
    print("PASS test_parse_simple_and_skips")


def test_nonpell_sum():
    year = 2018
    # Both components present -> summed.
    row = _mk_row("130794", year, {
        "completion.completion_rate_four_year_150_pell": 0.90,
        "completion.completion_rate_four_year_150_loan_nopell": 0.40,
        "completion.completion_rate_four_year_150_noloan_nopell": 0.55,
    })
    out = fs.parse_row(row, year)
    assert out["grad_rate_pell"] == 0.90
    assert abs(out["grad_rate_nonpell"] - 0.95) < 1e-9
    # Only one component -> no non-Pell value (don't invent).
    row2 = _mk_row("130794", year, {
        "completion.completion_rate_four_year_150_loan_nopell": 0.40,
    })
    assert "grad_rate_nonpell" not in fs.parse_row(row2, year)
    print("PASS test_nonpell_sum")


def test_net_price_branch():
    year = 2018
    # Public school: only _PUB (public) populated.
    pub = _mk_row("110635", year, {
        "cost.net_price.public.by_income_level.0-30000": 13862,
        "cost.net_price.public.by_income_level.110001-plus": 20054,
    })
    out = fs.parse_row(pub, year)
    assert out["net_price_0_30k"] == 13862
    assert out["net_price_110k_plus"] == 20054
    assert "net_price_30_48k" not in out

    # Private school: only the private control populated -> same column.
    priv = _mk_row("186131", year, {
        "cost.net_price.private.by_income_level.0-30000": 9500,
    })
    assert fs.parse_row(priv, year)["net_price_0_30k"] == 9500
    print("PASS test_net_price_branch")


def test_url_field_count():
    url = fs.build_url(["100663", "186131"], 2018, 0, "DEMO_KEY")
    # id + simple + 2 nonpell components + 4 controls * 5 bands
    expected = 1 + len(fs.SIMPLE_FIELDS) + 2 + 4 * 5
    n = url.count("2018.") + 1  # +1 for the bare "id" field
    assert n == expected, f"field count {n} != {expected}"
    assert "186131" in url and "DEMO_KEY" in url
    print(f"PASS test_url_field_count ({expected} fields/request)")


def test_write_outputs():
    records = {
        (100663, 2018): {"ug_size": 13284, "acceptance_rate": 0.8854,
                         "net_price_0_30k": 13862},
        (130794, 2017): {"grad_rate_6yr": 0.97, "grad_rate_pell": 0.90,
                         "grad_rate_nonpell": 0.95},
    }
    with tempfile.TemporaryDirectory() as d:
        fs.OUT_DIR = Path(d)
        fs.OUT_LONG = fs.OUT_DIR / "scorecard_raw.csv"
        fs.OUT_WIDE = fs.OUT_DIR / "scorecard_wide.csv"
        long_rows, wide_rows = fs.write_outputs(records)
        assert long_rows == 6, long_rows
        assert wide_rows == 2, wide_rows
        long_txt = fs.OUT_LONG.read_text().splitlines()
        assert long_txt[0] == "unitid,year,variable,value"
        # Sorted by (uid, year): 130794/2017 row group precedes 100663? No --
        # 100663 < 130794 so it comes first.
        assert long_txt[1].startswith("100663,2018,")
        wide_hdr = fs.OUT_WIDE.read_text().splitlines()[0]
        assert wide_hdr.startswith("unitid,year,")
        assert "grad_rate_nonpell" in wide_hdr
        assert "net_price_110k_plus" in wide_hdr
    print("PASS test_write_outputs")


def main():
    test_parse_simple_and_skips()
    test_nonpell_sum()
    test_net_price_branch()
    test_url_field_count()
    test_write_outputs()
    print("\nALL OFFLINE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
