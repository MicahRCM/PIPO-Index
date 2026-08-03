"""Scrape College Navigator's reported *Average net price* for each institution.

WHY: the 2024 rerun's cost file (costafterscholarship.xlsx) shipped a wrong
"Average Cost" (it does not correspond to the 5 income bands it lists). The 5
bands are correct (IPEDS 2023-24 provisional, matching Navigator), but the
overall average is the enrollment-WEIGHTED mean, which Navigator reports
directly and which is NOT recoverable from the 5 bands alone. IPEDS hasn't
released 2023-24 as a bulk file yet, so Navigator is the only source.

Per school: match the app's stored 5 bands to a Navigator year column and take
THAT column's average (guarantees the average matches the bands shown); if no
column matches, fall back to the most-recent year's average.

Output: data/navigator_avg_net_price.csv  (unitid, nav_avg_net_price, year, matched)
"""
import csv, json, re, sys, time, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INST = REPO / "web" / "data" / "institutions.json"
OUT  = REPO / "data" / "navigator_avg_net_price.csv"
BANDS = ["net_price_0_30k","net_price_30_48k","net_price_48_75k","net_price_75_110k","net_price_110k_plus"]
LABELS = ["$0 - $30,000","$30,001 - $48,000","$48,001 - $75,000","$75,001 - $110,000","$110,001 and more"]

def fetch(unitid, retries=3):
    url=f"https://nces.ed.gov/collegenavigator/?id={unitid}&fa=y"
    for a in range(retries):
        try:
            req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (PIPO-Index net-price fix)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8","ignore")
        except Exception:
            time.sleep(1.5*(a+1))
    return None

def parse(html):
    """-> list of columns [{'avg':int,'bands':[5 ints|None]}], oldest->newest."""
    if not html: return []
    i=html.find("Average Net Price for Full-Time Beginning")
    if i==-1: return []
    txt=re.sub(r"<[^>]+>"," ",html[i:i+3500]); txt=txt.replace("&ndash;","-"); txt=re.sub(r"\s+"," ",txt)
    m=re.search(r"Average net price\s+((?:\$[\d,]+\s*){1,5})", txt)
    if not m: return []
    avgs=[int(x.replace(",","")) for x in re.findall(r"\$([\d,]+)", m.group(1))]
    ncol=len(avgs)
    bi=txt.find("Average net price by Income")
    band_cols=[[None]*ncol for _ in range(5)]
    if bi!=-1:
        sub=txt[bi:]
        # values for bracket k = dollar amounts between its label and the next label
        for k,lab in enumerate(LABELS):
            j=sub.find(lab)
            if j==-1: continue
            start=j+len(lab)
            end=sub.find(LABELS[k+1]) if k+1<len(LABELS) else start+200
            vals=[int(x.replace(",","")) for x in re.findall(r"\$([\d,]+)", sub[start:end])]
            vals=vals[:ncol]
            for c in range(len(vals)): band_cols[k][c]=vals[c]
    return [{"avg":avgs[c],"bands":[band_cols[k][c] for k in range(5)]} for c in range(ncol)]

def choose(cols, stored):
    sb=[round(x) if isinstance(x,(int,float)) else None for x in stored]
    for c in reversed(range(len(cols))):
        if cols[c]["bands"]==sb:
            return cols[c]["avg"], True
    for c in reversed(range(len(cols))):
        if cols[c]["avg"] is not None:
            return cols[c]["avg"], False
    return None, False

def main():
    rows=json.load(open(INST)); rows=rows["data"] if isinstance(rows,dict) else rows
    targets=[]
    for r in rows:
        m=r.get("metrics",r)
        if any(isinstance(m.get(b),(int,float)) for b in BANDS):
            targets.append((r["unitid"],[m.get(b) for b in BANDS]))
    limit=int(sys.argv[1]) if len(sys.argv)>1 else len(targets)
    targets=targets[:limit]
    out=[]
    for n,(uid,stored) in enumerate(targets,1):
        avg,matched=choose(parse(fetch(uid)),stored)
        out.append({"unitid":uid,"nav_avg_net_price":avg if avg is not None else "","matched":int(matched)})
        if n%50==0 or n==len(targets): print(f"  {n}/{len(targets)} (last uid {uid} -> {avg} matched={matched})", flush=True)
        time.sleep(0.4)
    with OUT.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["unitid","nav_avg_net_price","matched"]); w.writeheader(); w.writerows(out)
    got=[o for o in out if o["nav_avg_net_price"]!=""]
    print(f"DONE {len(got)}/{len(out)} averages; matched-by-bands {sum(o['matched'] for o in out)}; -> {OUT}")

if __name__=="__main__": main()
