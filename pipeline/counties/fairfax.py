"""
Fairfax County, VA: sales the county assessor itself coded as atypical, priced
far above the pre-sale assessment.

Source: Fairfax County Department of Tax Administration tables on the county's
ArcGIS open-data services (no key), read 2026-11-21. Sales current to
2026-09-17 when read (about two months behind).
  OpenData_A5/1  Sales Data         PARID, SALEDT, PRICE, SALEVAL_DESC
  OpenData_A6/2  Assessed Values    APRTOT (TAXYR 2026, values as of 2026-01-01), PRITOT (prior year)
  OpenData_A6/1  Parcel Data        LUC_DESC (land use)
  OpenData_A7/1  Legal Description  address, ZIP, acres
  OpenData_A7/2  Dwelling Data      SFLA, RMBED, YRBLT, YRREMOD, GRADE_DESC

Why not a comps screen here: every Fairfax sale carries a validity code set by
the assessor after review, including "Non-representative price based on comps"
(1,326 sales 2025+) and "Atypical price - could not be verified" (252). That is
the county's own comparable-sales judgement. This script takes those two codes,
keeps single-parcel residential sales priced at >= RATIO x the pre-sale
assessment, and sets aside new construction / recent remodels by the dwelling
record. The codes say a price was unusual, not in which direction; the ratio
keeps only the high side.

Pre-sale assessment: 2025 sales -> PRITOT (tax year 2025, as of 2025-01-01);
2026 sales -> APRTOT (tax year 2026, as of 2026-01-01).

No owner fields are requested (none of these tables has owner names except
none used here).

    python3 counties/fairfax.py  -> .cache/fairfax/screen.json + table
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.dirname(HERE), ".cache", "fairfax")
B = "https://services1.arcgis.com/ioennV6PpG5Xodq0/ArcGIS/rest/services"
ATYPICAL = ("Non-representative price based on comps", "Atypical price - could not be verified")
RATIO = 1.5


def query(layer, where, fields, page=1000):
    out, off = [], 0
    while True:
        data = urllib.parse.urlencode({"where": where, "outFields": fields, "f": "json", "returnGeometry": "false",
                                       "resultOffset": off, "resultRecordCount": page, "orderByFields": "OBJECTID"}).encode()
        for attempt in range(4):
            try:
                req = urllib.request.Request(f"{B}/{layer}/query", data=data, headers={"User-Agent": "dc-realestate-pipeline"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    d = json.load(r)
                break
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(5)
        if "error" in d:
            raise RuntimeError(f"{layer}: {d['error']} ({where[:80]})")
        f = d.get("features", [])
        out += [x["attributes"] for x in f]
        if len(f) < page and not d.get("exceededTransferLimit"):
            return out
        off += len(f)


def by_parid(layer, parids, fields):
    out = []
    ps = sorted(parids)
    for i in range(0, len(ps), 150):
        inl = ",".join("'" + p.replace("'", "''") + "'" for p in ps[i:i + 150])
        out += query(layer, f"PARID IN ({inl})", fields)
    return out


def day(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d") if ms else None


def main():
    os.makedirs(CACHE, exist_ok=True)
    allsales = query("OpenData_A5/FeatureServer/1", "SALEDT >= DATE '2025-01-01' AND PRICE > 0",
                     "PARID,SALEDT,PRICE,SALEVAL_DESC")
    for s in allsales:
        s["date"] = day(s["SALEDT"])
    report = {"sales_2025_plus_price_gt0": len(allsales), "latest_sale": max(s["date"] for s in allsales),
              "atypical_coded": sum(1 for s in allsales if s["SALEVAL_DESC"] in ATYPICAL)}
    cand = [s for s in allsales if s["SALEVAL_DESC"] in ATYPICAL]
    ids = {s["PARID"] for s in cand}
    av = {a["PARID"]: a for a in by_parid("OpenData_A6/FeatureServer/2", ids, "PARID,TAXYR,APRTOT,PRITOT")}
    luc = {a["PARID"]: a.get("LUC_DESC") for a in by_parid("OpenData_A6/FeatureServer/1", ids, "PARID,LUC_DESC")}
    legal = {a["PARID"]: a for a in by_parid("OpenData_A7/FeatureServer/1", ids,
                                             "PARID,ADRNO,ADRADD,ADRDIR,ADRSTR,ADRSUF,CITYNAME,ZIP1,ACRES")}
    dw = {}
    for a in by_parid("OpenData_A7/FeatureServer/2", ids, "PARID,SFLA,RMBED,YRBLT,YRREMOD,GRADE_DESC,STYLE_DESC"):
        dw.setdefault(a["PARID"], a)
    rows, reasons = [], Counter()
    for s in cand:
        a = av.get(s["PARID"]) or {}
        assessed = (a.get("PRITOT") if s["date"] < "2026-01-01" else a.get("APRTOT")) or 0
        d = dw.get(s["PARID"]) or {}
        l = legal.get(s["PARID"]) or {}
        r = {"parid": s["PARID"], "date": s["date"], "price": s["PRICE"], "code": s["SALEVAL_DESC"],
             "assessed_pre_sale": assessed, "ratio": round(s["PRICE"] / assessed, 2) if assessed else None,
             "land_use": luc.get(s["PARID"]), "sqft": d.get("SFLA"), "beds": d.get("RMBED"), "year_built": d.get("YRBLT"),
             "year_remodeled": d.get("YRREMOD"), "grade": d.get("GRADE_DESC"), "acres": l.get("ACRES"),
             "address": " ".join(str(x) for x in (l.get("ADRNO"), l.get("ADRADD"), l.get("ADRDIR"), l.get("ADRSTR"),
                                                  l.get("ADRSUF")) if x) + f", {l.get('CITYNAME') or ''} {l.get('ZIP1') or ''}"}
        yr = int(s["date"][:4])
        if not assessed:
            r["set_aside"] = "no pre-sale assessment"
        elif not d:
            r["set_aside"] = "no dwelling record (not a house, or land)"
        elif (d.get("YRBLT") or 0) >= yr - 1:
            r["set_aside"] = f"new construction (built {d.get('YRBLT')})"
        elif (d.get("YRREMOD") or 0) >= yr - 1:
            r["set_aside"] = f"remodeled {d.get('YRREMOD')}"
        elif r["ratio"] < RATIO:
            r["set_aside"] = f"price < {RATIO}x pre-sale assessment"
        reasons[r.get("set_aside", "KEPT").split(" (")[0]] += 1
        rows.append(r)
    report["atypical_breakdown"] = dict(reasons)
    kept = sorted([r for r in rows if "set_aside" not in r], key=lambda r: -r["ratio"])
    json.dump({"report": report, "kept": kept, "all_atypical": rows}, open(os.path.join(CACHE, "screen.json"), "w"), indent=1)
    print(json.dumps(report, indent=1))
    print(f"\nAssessor-coded atypical house sales at >= {RATIO}x pre-sale assessment ({len(kept)}):")
    for r in kept:
        print(f"  {r['date']} ${r['price']:>10,.0f} x{r['ratio']:<5} vs ${r['assessed_pre_sale']:>9,.0f}  {r['sqft']}sf {r['beds']}bd built {r['year_built']}"
              f" remod {r['year_remodeled']}  {r['land_use']}  [{r['code'][:30]}]  {r['address']}")


if __name__ == "__main__":
    main()
