"""Regenerate the embedded datasets in js/{CAS,VAI,VAM,VAC}.js from the 2024
tool spreadsheets in `data/2024 tool data/`. Non-destructive to the JS logic:
only the data-array assignment line(s) are replaced; all code/constants stay.

Schema per data/2024 tool data/SCHEMA_MAP.md. Join on ipedsid.
VAC `C` ("VA Overall Performance") is not in any spreadsheet — regenerated here
via the documented fit C = 0.587*VA_Ret_pp + 0.801*VA_Grad_pp + 1.17 (R^2=.9992),
flagged PROVISIONAL pending confirmation.

Usage:
  python3 data_pipeline/regen_tool_data.py            # write staged files + report
  python3 data_pipeline/regen_tool_data.py --inplace  # overwrite js/*.js (git-reversible)
"""
import argparse, json, re, openpyxl
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TD = REPO / "data" / "2024 tool data"
JS = REPO / "js"

STATE = {  # 2-letter -> full name (matches the tools' `states`/REGION_STATES)
 "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
 "CO":"Colorado","CT":"Connecticut","DE":"Delaware","DC":"District of Columbia",
 "FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois",
 "IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
 "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota",
 "MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
 "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York",
 "NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon",
 "PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
 "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia",
 "WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming",
 "PR":"Puerto Rico","GU":"Guam","VI":"Virgin Islands","AS":"American Samoa",
 "MP":"Northern Mariana Islands","FM":"Federated States of Micronesia",
}


def load(fn):
    ws = openpyxl.load_workbook(TD / fn, data_only=True).active
    rows = list(ws.iter_rows(values_only=True))
    H = {c: i for i, c in enumerate(rows[0])}
    return [r for r in rows[1:] if r[H["ipedsid" if "ipedsid" in H else "ipedsid"]] is not None], H


def num(v):        # numeric cost -> int; blank/str -> "NA"
    if v is None or isinstance(v, str) or v == "":
        return "NA"
    return int(round(float(v)))


def pp(v):         # decimal -> percent points, 1 decimal
    return round(float(v) * 100, 1) if v is not None else None


def state_full(ab):
    return STATE.get((ab or "").strip().upper(), (ab or "").strip())


def replace_assignment(src, varname, literal, template=False):
    """Replace `var/let <varname> = <...>` (single-line) with the new value."""
    rhs = f"`{literal}`" if template else literal
    pat = re.compile(rf"((?:var|let|const)\s+{re.escape(varname)}\s*=\s*)(?:`[^`]*`|\[.*?\](?=\s*(?:;|$)))",
                     re.MULTILINE)
    new, n = pat.subn(lambda m: m.group(1) + rhs, src, count=1)
    if n != 1:
        raise SystemExit(f"could not locate assignment for {varname} (matched {n})")
    return new


def dumps(records):
    return json.dumps(records, separators=(",", ":"), ensure_ascii=False)


def build():
    idx, HI = load("valuedaddedindex.xlsx")
    cost, HC = load("costafterscholarship.xlsx")
    dbN, HN = load("valuedaddeddatabase.xlsx")
    dbB, HB = load("valuedaddeddatabaseBA.xlsx")

    # index keyed by ipedsid -> metadata
    meta = {}
    for r in idx:
        uid = int(r[HI["ipedsid"]])
        meta[uid] = {
            "name": r[HI["Name"]],
            "usn": r[HI["US News Rank"]],
            "va_ret": pp(r[HI["VA Retention"]]),
            "va_grad": pp(r[HI["VA Graduation"]]),
            "rank": r[HI["Rank"]],
            "nationalu": int(r[HI["nationalu"]]),
            "pubpriv": 1 if str(r[HI["pubpriv"]]).lower() == "public" else 2,
            "state": state_full(r[HI["state"]]),
        }
    costmap = {int(r[HC["ipedsid"]]): r for r in cost}

    out = {}

    # ---- CAS: A,B,C,D,F,G,H,I,J,K,L,M (exact order, no E) ----
    cas = []
    for uid, cr in costmap.items():
        m = meta.get(uid, {})
        cas.append({
            "A": cr[HC["Name"]], "B": m.get("usn"), "C": uid,
            "D": m.get("nationalu", ""), "F": m.get("pubpriv", ""),
            "G": m.get("state", ""),
            "H": num(cr[HC["Cost under 30"]]), "I": num(cr[HC["Cost 30-48"]]),
            "J": num(cr[HC["Cost 48-75"]]), "K": num(cr[HC["Cost 75-110"]]),
            "L": num(cr[HC["Cost over 110"]]), "M": num(cr[HC["Average Cost"]]),
        })
    out["CAS"] = cas

    # ---- VAI: two arrays (National / Other) ----
    def vai_rows(db, H):
        res = []
        for r in db:
            res.append({
                "Name": r[H["Name"]],
                "VA Retention": pp(r[H["VA Retention"]]),
                "VA Graduation": pp(r[H["VA Graduation"]]),
                "Graduation Rate": pp(r[H["Graduation Rate"]]),
                "US News Rank": r[H["US News Rank"]],
                "Rank": r[H["Rank"]],
                "UNITID": int(r[H["ipedsid"]]),
            })
        return res
    out["VAI_1"] = vai_rows(dbN, HN)
    out["VAI_2"] = vai_rows(dbB, HB)

    # ---- VAM: A,B,C,D,E,F,G,I,J ----
    vam = []
    for uid, m in meta.items():
        vam.append({
            "A": m["name"], "B": m["va_ret"], "C": m["va_grad"], "D": m["usn"],
            "E": m["rank"], "F": uid, "G": m["nationalu"], "I": m["pubpriv"], "J": m["state"],
        })
    out["VAM"] = vam

    # ---- VAC: A,B,C,D,E,F,H,I,U,V,W,X,Y,Z  (C = provisional fit) ----
    vac = []
    for uid, m in meta.items():
        cr = costmap.get(uid)
        c_val = round(0.587 * (m["va_ret"] or 0) + 0.801 * (m["va_grad"] or 0) + 1.17, 1)
        rec = {"A": m["name"], "B": m["usn"], "C": c_val, "D": m["rank"], "E": uid,
               "F": m["nationalu"], "H": m["pubpriv"], "I": m["state"]}
        if cr:
            rec.update({"Z": num(cr[HC["Average Cost"]]), "U": num(cr[HC["Cost under 30"]]),
                        "V": num(cr[HC["Cost 30-48"]]), "W": num(cr[HC["Cost 48-75"]]),
                        "X": num(cr[HC["Cost 75-110"]]), "Y": num(cr[HC["Cost over 110"]])})
        else:
            for k in "ZUVWXY":
                rec[k] = "NA"
        vac.append(rec)
    out["VAC"] = vac
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inplace", action="store_true")
    args = ap.parse_args()
    out = build()

    edits = [
        ("CAS.js", [("data_1", dumps(out["CAS"]), True)]),
        ("VAI.js", [("data_1", dumps(out["VAI_1"]), True), ("data_2", dumps(out["VAI_2"]), True)]),
        ("VAM.js", [("university_data", dumps(out["VAM"]), False)]),
        ("VAC.js", [("university_data", dumps(out["VAC"]), False)]),
    ]
    for fn, subs in edits:
        src = (JS / fn).read_text()
        for var, lit, tmpl in subs:
            src = replace_assignment(src, var, lit, template=tmpl)
        target = (JS / fn) if args.inplace else (JS / (fn + ".new"))
        target.write_text(src)

    print(f"CAS  records: {len(out['CAS'])}")
    print(f"VAI  National: {len(out['VAI_1'])}  Other: {len(out['VAI_2'])}")
    print(f"VAM  records: {len(out['VAM'])}")
    print(f"VAC  records: {len(out['VAC'])}  (C = PROVISIONAL fit)")
    print("written " + ("IN PLACE to js/*.js" if args.inplace else "to js/*.js.new (staged)"))
    # sample record per tool for eyeballing
    print("\nsample CAS[0]:", dumps(out["CAS"][:1]))
    print("sample VAM[0]:", dumps(out["VAM"][:1]))
    print("sample VAC[0]:", dumps(out["VAC"][:1]))
    print("sample VAI_1[0]:", dumps(out["VAI_1"][:1]))


if __name__ == "__main__":
    main()
