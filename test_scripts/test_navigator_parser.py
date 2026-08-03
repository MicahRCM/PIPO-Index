"""Validate the College Navigator net-price parser against two known cases:
   UConn (129020) -> correct average 25310 ; CSUSB (110510) -> 5231.
The parser matches the app's stored 5 bands to a year column and returns THAT
year's reported average net price (so the average always matches the bands shown)."""
import re, urllib.request, json

def fetch(unitid):
    url=f"https://nces.ed.gov/collegenavigator/?id={unitid}&fa=y"
    req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8","ignore")

def parse(html):
    """Return dict: years -> {'avg': int|None, 'bands':[5 ints]}."""
    txt=re.sub(r"<[^>]+>"," ",html); txt=re.sub(r"&ndash;","-",txt); txt=re.sub(r"\s+"," ",txt)
    # 1) headline average row: "Average net price $a $b $c" (1-3 yrs)
    #    anchored so we don't grab "by Income"
    seg=txt
    i=seg.find("Average Net Price for Full-Time Beginning")
    if i==-1: return None
    seg=seg[i:i+3000]
    # years header before the avg row
    yrs=re.findall(r"(20\d\d-20\d\d)", seg)
    m=re.search(r"Average net price\s+((?:\$[\d,]+\s*){1,4})", seg)
    avgs=[int(x.replace(",","")) for x in re.findall(r"\$([\d,]+)", m.group(1))] if m else []
    # 2) by-income table: five rows, each "$label $y1 $y2 $y3"
    bi=seg.find("Average net price by Income")
    band_rows=[]
    if bi!=-1:
        sub=seg[bi:bi+1500]
        labels=["$0 - $30,000","$30,001 - $48,000","$48,001 - $75,000","$75,001 - $110,000","$110,001 and more"]
        for lab in labels:
            j=sub.find(lab)
            if j==-1: band_rows.append([]); continue
            after=sub[j+len(lab): j+len(lab)+120]
            vals=[int(x.replace(",","")) for x in re.findall(r"\$([\d,]+)", after)]
            band_rows.append(vals)
    # align columns: assume the LAST N year-columns align across avg + bands
    ncol=len(avgs)
    out={}
    for c in range(ncol):
        yr=yrs[-ncol+c] if len(yrs)>=ncol else str(c)
        bands=[br[-ncol+c] if len(br)>=ncol else None for br in band_rows]
        out[yr]={"avg":avgs[c],"bands":bands}
    return out

def pick(cols, stored_bands):
    """Choose the year column whose bands match the app's stored bands; else most recent."""
    sb=[round(x) for x in stored_bands]
    for yr in reversed(list(cols)):
        if [b for b in cols[yr]["bands"]]==sb:
            return yr, cols[yr]["avg"]
    # fallback: most recent year with an avg
    for yr in reversed(list(cols)):
        if cols[yr]["avg"] is not None:
            return yr+"(fallback)", cols[yr]["avg"]
    return None, None

CASES={129020:([15193,16339,20608,28285,33797],25310),
       110510:([2681,2680,4735,7745,14316],5231)}
for uid,(bands,expected) in CASES.items():
    cols=parse(fetch(uid))
    yr,avg=pick(cols,bands)
    ok="OK" if avg==expected else "MISMATCH"
    print(f"{uid}: matched year={yr} avg={avg} expected={expected} [{ok}]")
    print("   parsed:", {y:(c['avg'],c['bands']) for y,c in cols.items()})
