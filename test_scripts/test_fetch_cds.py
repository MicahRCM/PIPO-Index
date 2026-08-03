#!/usr/bin/env python3
"""
test_fetch_cds.py — validate the CDS parser on known-good Common Data Sets.

Covers all three extraction paths:
  * text         — line-oriented parser (Agnes Scott, Michigan)
  * AcroForm     — fillable-PDF form fields read with pypdf
                   (Wake Forest, Central Michigan 2024-25)
  * xlsx         — spreadsheet CDS read with openpyxl (Vanderbilt 2024-25)

Files are cached under data/cds_cache/; if missing they are downloaded once with
curl. Each file's type is sniffed from its magic bytes, exactly as the pipeline
does, so the right fallback is exercised.

Run:  python3 test_scripts/test_fetch_cds.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "data_pipeline"))

import fetch_cds  # noqa: E402

CACHE = os.path.join(ROOT, "data", "cds_cache")

CASES = [
    {
        "name": "Agnes Scott College (text path)",
        "file": "agnes_scott.pdf",
        "url": "https://www.agnesscott.edu/assets/documents/institutional-research/cds_2024_2025.pdf",
        "expect": {
            "cds_year": "2024-2025",
            "hs_gpa": 3.71,
            "pct_top10_hs": 18.5,
            "pct_need_met": 64.4,
            "need_aid_total": 26763504,
            "merit_aid_total": 4717985,
            "avg_aid_package": 43834,
            "pct_commuter": 15.7,
            "pct_demonstrated_need": 87.62,  # H2 line C 184 / line A 210
        },
    },
    {
        "name": "University of Michigan-Ann Arbor (text path)",
        "file": "michigan.pdf",
        "url": "https://obp.umich.edu/wp-content/uploads/pubdata/cds/CDS_2024-25_UMAA.pdf",
        # Michigan does not report top-10% inline (blank in cds_sample.csv).
        "expect": {
            "cds_year": "2024-2025",
            "hs_gpa": 3.9,
            "pct_need_met": 91.0,
            "need_aid_total": 310707956,
            "merit_aid_total": 126917187,
            "avg_aid_package": 35086,
            "pct_commuter": 75.0,
            "pct_demonstrated_need": 42.43,  # H2 line C 3,151 / line A 7,426
        },
        "blank": ["pct_top10_hs"],
    },
    {
        # Fillable AcroForm PDF — extract_text() returns blank values; the
        # pypdf form-field fallback must recover them. Wake Forest is test-blind
        # for GPA, so hs_gpa stays empty.
        "name": "Wake Forest University (AcroForm path)",
        "file": "wake_forest.pdf",
        "url": "https://prod.wp.cdn.aws.wfu.edu/sites/202/2025/07/CDS-2024-2025-fillable-WFU.pdf",
        "expect": {
            "cds_year": "2024-2025",
            "pct_top10_hs": 64.2,
            "pct_need_met": 95.57,
            "need_aid_total": 80861285,
            "merit_aid_total": 10029722,
            "avg_aid_package": 72851,
            "pct_commuter": 25.0,
            "pct_demonstrated_need": 19.73,  # AcroForm FRSH_FT_ND_N 274 / FRSH_FT_N 1389
        },
        "blank": ["hs_gpa"],
    },
    {
        # The two-column/fillable example from the brief: Central Michigan's
        # 2024-25 CDS is the official fillable template, recovered via the same
        # form-field path.
        "name": "Central Michigan University (AcroForm path)",
        "file": "central_michigan.pdf",
        "url": "https://www.cmich.edu/docs/default-source/academic-affairs-division/academic-administration/academic-planning-analysis/reports-(public)/common-data-sets/cds-2024-2025.pdf?sfvrsn=b0421437_9",
        "expect": {
            "cds_year": "2024-2025",
            "hs_gpa": 3.51,
            "pct_top10_hs": 26.2,
            "pct_need_met": 70.0,
            "need_aid_total": 67613922,
            "merit_aid_total": 13825392,
            "avg_aid_package": 21393,
            "pct_commuter": 59.2,
            "pct_demonstrated_need": 64.4,  # AcroForm FRSH_FT_ND_N 1409 / FRSH_FT_N 2188
        },
    },
    {
        # Spreadsheet CDS — openpyxl path. Vanderbilt publishes the CDS as .xlsx;
        # the workbook has no in-file year header, so the year comes from the URL.
        "name": "Vanderbilt University (xlsx path)",
        "file": "vanderbilt.xlsx",
        "url": "https://cdn.vanderbilt.edu/vu-wpfsx/wp-content/uploads/sites/70/2025/11/CDS_2024-2025.xlsx",
        "expect": {
            "cds_year": "2024-2025",
            "hs_gpa": 3.89,
            "pct_top10_hs": 90.1,
            "pct_need_met": 100.0,
            "need_aid_total": 258596820,
            "merit_aid_total": 37624674,
            "avg_aid_package": 78832,
            "pct_commuter": 16.0,
            "pct_demonstrated_need": 51.66,  # xlsx H2 line C 842 / line A 1,630
        },
    },
]


def ensure(path, url):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return
    os.makedirs(CACHE, exist_ok=True)
    subprocess.run(["curl", "-sL", "-A", fetch_cds.UA, "-o", path, url],
                   check=True, timeout=180)


def parse(path, url):
    """Sniff the file type and run the matching parser, then assemble a row."""
    with open(path, "rb") as fh:
        head = fh.read(8)
    if head[:2] == b"PK":
        values, fy = fetch_cds.xlsx_values(path, url)
    else:
        values, fy = fetch_cds.parse_pdf_file(path, url)
    if not values:
        return None, "parse_fail", "no_values"
    return fetch_cds._assemble_row([(values, fy)])


# Synthetic H2 blocks exercising the two real-world text layouts for
# pct_demonstrated_need (line C / line A, first-time first-year column), so the
# tricky wrapping logic is covered offline without a network fetch.
_H2_AGNES_STYLE = """
Common Data Set 2024-2025
A Number of degree-seeking undergraduate students
(CDS Item B1 if reporting on Fall 2024 cohort) 210 830 2
B Number of students in line a who applied for need-based
199 727 2
financial aid
C Number of students in line b who were determined to
184 698 2
have financial need
D Number of students in line c who were awarded any
184 698 2
financial aid
"""

_H2_MICHIGAN_STYLE = """
Common Data Set 2024-2025
A. Number of degree-seeking undergraduate
7,426 32,179 1,309
students
B. Number of students in line (A) who applied for
5,525 17,553 443
need-based financial aid
C. Number of students in line (B) who were
3,151 12,150 287
determined to have financial need
D. Number of students in line (C) who were awarded
3,090 11,968 260
any financial aid
"""


def test_demonstrated_need_layouts():
    failures = 0
    for label, text, exp in [
        ("agnes-style (numbers after label)", _H2_AGNES_STYLE, 87.62),
        ("michigan-style (numbers mid-label)", _H2_MICHIGAN_STYLE, 42.43),
    ]:
        pct, _ = fetch_cds._demonstrated_need_from_text(text)
        ok = pct is not None and abs(pct - exp) < 0.05
        if not ok:
            failures += 1
        print(f"  [{'OK ' if ok else 'FAIL'}] {label:36s} expected={exp} got={pct}")
    return failures


def test_landing_link_resolver():
    """_find_cds_link picks the newest same-CDS file link, resolving relative
    URLs and ignoring non-CDS PDFs — fully offline."""
    failures = 0
    html = '''
      <a href="/docs/newsletter.pdf">news</a>
      <a href="/ir/CDS_2023-2024.pdf">CDS 23-24</a>
      <a href="../data/common-data-set-2024-2025.xlsx">CDS 24-25</a>
      <a href="https://x.edu/random.pdf">other</a>
    '''
    got = fetch_cds._find_cds_link(html, "https://college.edu/ir/index.html")
    exp = "https://college.edu/data/common-data-set-2024-2025.xlsx"  # newest yr
    ok = got == exp
    failures += 0 if ok else 1
    print(f"  [{'OK ' if ok else 'FAIL'}] newest CDS link          expected={exp} got={got}")

    none_html = '<a href="/brochure.pdf">x</a><a href="/map.pdf">y</a>'
    got2 = fetch_cds._find_cds_link(none_html, "https://college.edu/")
    ok2 = got2 is None
    failures += 0 if ok2 else 1
    print(f"  [{'OK ' if ok2 else 'FAIL'}] no CDS link -> None      got={got2}")
    return failures


def main():
    failures = 0
    print("\n=== H2 pct_demonstrated_need text layouts (offline) ===")
    failures += test_demonstrated_need_layouts()
    print("\n=== landing-page CDS link resolver (offline) ===")
    failures += test_landing_link_resolver()
    for case in CASES:
        path = os.path.join(CACHE, case["file"])
        ensure(path, case["url"])
        row, status, reason = parse(path, case["url"])
        print(f"\n=== {case['name']} (status={status}) ===")
        assert status == "ok", f"  parse status {status}/{reason}"

        for field, exp in case["expect"].items():
            got = row[field]
            if isinstance(exp, float):
                ok = isinstance(got, (int, float)) and abs(got - exp) < 0.05
            else:
                ok = got == exp
            flag = "OK " if ok else "FAIL"
            if not ok:
                failures += 1
            print(f"  [{flag}] {field:16s} expected={exp!r:14} got={got!r}")

        for field in case.get("blank", []):
            ok = row[field] == ""
            if not ok:
                failures += 1
            print(f"  [{'OK ' if ok else 'FAIL'}] {field:16s} expected=blank   got={row[field]!r}")

    print("\n" + ("ALL TESTS PASSED" if failures == 0 else f"{failures} FAILURES"))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
