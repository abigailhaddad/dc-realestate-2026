"""
Arlington County, VA: the same "sold far above anything comparable" screen as DC.

Source: Arlington's public real-estate DataHub API (no key), read 2026-11-21:
  https://datahub-v2.arlingtonva.us/api/RealEstate/{SalesHistory,Property,Assessment,ImprovementInterior}
Sales are current to within days (latest saleDate 2026-11-18 when first read).

What Arlington records that DC doesn't:
  - salesTypeCode on every transfer. Codes used here (descriptions as published):
      None                 = coded as a market sale
      'P'  "Not Listed MLS/Online, Pub..."  -> the county itself marks the sale as
                             off-market; kept and flagged, never dropped
      'G'  "New Construction"               -> explains a high price
      '4' / 'F' "Multiple RPCs ..."         -> multi-property deal; grouped by deed
                             document number and compared with the summed assessment
      gifts, wills, quitclaims, corrections, partial interests, lease assignments,
      "Not Market Sale" (5, N)              -> not market sales; dropped and counted
  - landRecordDocumentNbr (deed document), so a multi-property deal groups exactly.

Owner fields (firstOwnerName, granteeName, ...) are never requested.

    python3 counties/arlington.py   -> .cache/arlington/screen.json + printed table
"""
from __future__ import annotations

import json
import os
import statistics
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.dirname(HERE), ".cache", "arlington")
API = "https://datahub-v2.arlingtonva.us/api/RealEstate"
PERMIT_API = "https://datahub-v2.arlingtonva.us/api/Permit/Permit"
SINCE = "2025-01-01"
NON_MARKET = {"2", "5", "N", "W", "D", "A", "6", "O", "7"}
MULTI = {"4", "F"}
# Arlington's neighborhoodNbr is fine-grained (340 codes; median 6 market house
# sales each since 2025), so comps use its first 4 digits (33 groups, median 12),
# a +/-365-day window and at least 8 comparables. DC used NBHD, +/-183 days, 10.
MIN_COMPS, MAX_HIGHER, PPSF_MULT = 8, 1, 1.3
WINDOW_DAYS, NBHD_DIGITS = 365, 4
MIN_YEARS, MAX_CAGR = 1.0, 0.08
N_RATIO = 1.3


def get(endpoint, params):
    url = f"{API}/{endpoint}?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "dc-realestate-pipeline"}), timeout=120) as r:
                d = json.load(r)
            if isinstance(d, dict) and "error" in d:
                raise RuntimeError(f"{endpoint}: {d['error'].get('message')}")
            return d
        except (OSError, json.JSONDecodeError):
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def get_all(endpoint, select, flt=None, page=20000):
    out, skip = [], 0
    while True:
        # $orderby on every selected field (2026-11-21): without a sort order the
        # server's $skip paging is unstable. The first pull returned 6,040
        # duplicate Property rows and silently missed 332 of the 4,079 properties
        # sold since 2025; the "73K duplicate sales rows" were the same artifact.
        p = {"$select": select, "$top": page, "$skip": skip, "$orderby": select}
        if flt:
            p["$filter"] = flt
        rows = get(endpoint, p)
        out += rows
        if len(rows) < page:
            return out
        skip += page


# Permit types that mean real construction (Arlington permitTypeCode /
# permitSubTypeCode values seen 2026-11-21). Trade-only permits, right-of-way
# and utility work don't count.
CONSTRUCTION_TYPES = {"Residential", "Demolition", "Commercial"}
CONSTRUCTION_SUBTYPES = {"Addition", "New", "Alteration"}


def permits(rpc):
    """Permits for one property. Only work fields are kept: the endpoint also
    returns owner and permit-holder names, which are dropped here unread."""
    url = PERMIT_API + "?" + urllib.parse.urlencode({"$filter": f"realEstatePropertyCode eq '{rpc}'", "$top": 500,
                                                     "$select": "issuedDate,permitTypeCode,permitSubTypeCode,permitDescriptionText"})
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "dc-realestate-pipeline"}), timeout=120) as r:
        rows = json.load(r)
    return rows if isinstance(rows, list) else []


def cached(name, fn):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, name + ".json")
    if os.path.exists(p):
        return json.load(open(p))
    d = fn()
    json.dump(d, open(p, "w"))
    return d


def main():
    sales_all = cached("sales_all", lambda: get_all(
        "SalesHistory", "realEstatePropertyCode,saleDate,saleAmt,salesTypeCode,salesTypeDsc,landRecordDocumentNbr"))
    props = cached("property", lambda: get_all(
        "Property", "realEstatePropertyCode,propertyClassTypeCode,propertyClassTypeDsc,neighborhoodNbr,"
                    "grossFloorAreaSquareFeetQty,propertyYearBuilt,lotSizeQty,propertyStreetNbr,"
                    "propertyStreetNbrNameText,propertyUnitNbr,propertyZipCode"))
    assess = cached("assessment", lambda: get_all(
        "Assessment", "realEstatePropertyCode,assessmentDate,totalValueAmt",
        flt="assessmentDate ge 2025-01-01T00:00:00Z"))
    # Living area: grossFloorAreaSquareFeetQty on Property is blank for houses
    # (51 of 3,835 market sales had it), so area = sum of finished area across the
    # dwelling's floors, falling back to base area for a floor with no finished
    # area recorded (basements are often 0 finished).
    interior = cached("interior", lambda: get_all("ImprovementInterior",
                      "realEstatePropertyCode,bedroomCnt,baseAreaSquareFeetQty,finishedAreaSquareFeetQty,floorNbr"))

    P = {p["realEstatePropertyCode"]: p for p in props}
    A = defaultdict(dict)
    for a in assess:
        A[a["realEstatePropertyCode"]][a["assessmentDate"][:4]] = a["totalValueAmt"] or 0
    beds, area = Counter(), Counter()
    for i in interior:
        beds[i["realEstatePropertyCode"]] += i.get("bedroomCnt") or 0
        fin = i.get("finishedAreaSquareFeetQty") or 0
        if (i.get("floorNbr") or "") != "B":          # above-grade floors only
            area[i["realEstatePropertyCode"]] += fin or (i.get("baseAreaSquareFeetQty") or 0)
    # The SalesHistory feed repeats some rows (4,239 exact duplicates once paging
    # was fixed 2026-11-21; the 72,794 first reported were our paging bug).
    seen, dedup = set(), []
    for s in sales_all:
        k = (s["realEstatePropertyCode"], s.get("saleDate"), s.get("saleAmt"), (s.get("landRecordDocumentNbr") or "").strip())
        if k not in seen:
            seen.add(k)
            dedup.append(s)
    sales_all = dedup
    doc_count = Counter((s.get("landRecordDocumentNbr") or "").strip() for s in sales_all)
    hist = defaultdict(list)
    for s in sales_all:
        if (s.get("saleAmt") or 0) > 0 and s.get("saleDate"):
            hist[s["realEstatePropertyCode"]].append((s["saleDate"][:10], s["saleAmt"], s.get("salesTypeCode")))

    recent = [s for s in sales_all if (s.get("saleDate") or "") >= SINCE and (s.get("saleAmt") or 0) > 0]
    report = {"sales_2025_plus_price_gt0": len(recent),
              "latest_sale_date": max(s["saleDate"][:10] for s in recent),
              "by_type": dict(Counter(s.get("salesTypeDsc") or "(none: market)" for s in recent).most_common())}

    # Transactions: multi-property codes grouped by deed document.
    txns, multi = [], defaultdict(list)
    for s in recent:
        code = (s.get("salesTypeCode") or "").strip()
        if code in NON_MARKET:
            continue
        if code in MULTI:
            multi[s.get("landRecordDocumentNbr") or (s["saleDate"][:10], s["saleAmt"])].append(s)
        else:
            txns.append([s])
    txns += list(multi.values())
    report["transactions_market_or_flagged"] = len(txns)

    def is_house(rpc):
        d = (P.get(rpc) or {}).get("propertyClassTypeDsc") or ""
        return d.startswith("511") or "Single Family" in d or "Twnhse" in d or "Townhouse" in d or "Detached" in d

    rows = []
    for t in txns:
        s0 = t[0]
        yr = s0["saleDate"][:4]
        rpcs = [s["realEstatePropertyCode"] for s in t]
        assessed = sum(A[r].get(yr, 0) for r in rpcs)
        p = P.get(rpcs[0]) or {}
        rows.append({"rpc": rpcs[0], "rpcs": rpcs, "date": s0["saleDate"][:10], "price": s0["saleAmt"],
                     "code": (s0.get("salesTypeCode") or "").strip() or None, "code_desc": s0.get("salesTypeDsc"),
                     "assessed_jan1": assessed, "ratio": s0["saleAmt"] / assessed if assessed else None,
                     "house": len(t) == 1 and is_house(rpcs[0]),
                     "nbhd": str(p.get("neighborhoodNbr"))[:NBHD_DIGITS] if p.get("neighborhoodNbr") else None,
                     "sqft": area.get(rpcs[0], 0), "beds": beds.get(rpcs[0], 0),
                     "year_built": p.get("propertyYearBuilt"), "class": p.get("propertyClassTypeDsc"),
                     "address": " ".join(str(x) for x in (p.get("propertyStreetNbrNameText"), p.get("propertyUnitNbr")) if x)})

    # Comps among single-property house sales coded as market sales.
    pool = defaultdict(list)
    for r in rows:
        if r["house"] and r["code"] is None and r["sqft"]:
            pool[r["nbhd"]].append(r)
    cands = []
    for r in rows:
        if not (r["house"] and r["sqft"]):
            continue
        d0 = date.fromisoformat(r["date"])
        comps = [c for c in pool[r["nbhd"]] if c["rpc"] != r["rpc"]
                 and abs((date.fromisoformat(c["date"]) - d0).days) <= WINDOW_DAYS
                 and abs(c["sqft"] - r["sqft"]) <= 0.25 * r["sqft"] and abs(c["beds"] - r["beds"]) <= 1]
        r["n_comps"] = len(comps)
        if len(comps) < MIN_COMPS:
            continue
        r["n_higher"] = sum(c["price"] >= r["price"] for c in comps)
        r["comps_median"] = statistics.median(c["price"] for c in comps)
        r["ppsf_mult"] = round((r["price"] / r["sqft"]) / statistics.median(c["price"] / c["sqft"] for c in comps), 2)
        if r["n_higher"] <= MAX_HIGHER and r["ppsf_mult"] >= PPSF_MULT:
            cands.append(r)

    # Own sale history.
    for r in cands:
        prior = [h for h in sorted(hist[r["rpc"]]) if h[0] < r["date"] and (h[2] or "") not in NON_MARKET | MULTI]
        if prior:
            pd, pp, _ = prior[-1]
            yrs = (date.fromisoformat(r["date"]) - date.fromisoformat(pd)).days / 365.25
            cagr = (r["price"] / pp) ** (1 / yrs) - 1 if yrs > 0 else None
            r.update(prev_date=pd, prev_price=pp, cagr=round(cagr, 4) if cagr is not None else None,
                     history_consistent=bool(yrs >= MIN_YEARS and cagr is not None and cagr <= MAX_CAGR))
        else:
            r["history_consistent"] = False
        yb = r.get("year_built") or 0
        r["explained"] = ("new construction (county code G)" if r["code"] == "G" else
                          "land sale (county code L; buyer paying for the lot)" if r["code"] == "L" else
                          "consistent with own sale history" if r["history_consistent"] else
                          f"rebuilt since previous sale (built {yb}, bought {r['prev_date'][:4]})"
                          if r.get("prev_date") and yb > int(r["prev_date"][:4]) else
                          f"new construction (built {yb})" if yb >= int(r["date"][:4]) - 1 else None)

    # Construction permits from two years before to the sale date, for what's
    # still unexplained (added 2026-11-21, same rule as DC and Maryland).
    for r in cands:
        if r["explained"]:
            continue
        lo = str(date.fromisoformat(r["date"]).replace(year=int(r["date"][:4]) - 2))
        hits = [p for p in permits(r["rpc"]) if lo <= (p.get("issuedDate") or "")[:10] <= r["date"]
                and (p.get("permitTypeCode") in CONSTRUCTION_TYPES or p.get("permitSubTypeCode") in CONSTRUCTION_SUBTYPES)]
        r["permits_in_window"] = [((p.get("issuedDate") or "")[:10], p.get("permitTypeCode"), p.get("permitSubTypeCode"),
                                   (p.get("permitDescriptionText") or "")[:120]) for p in hits]
        if hits:
            r["explained"] = "construction permit in the two years before the sale"

    # Assessor-coded "N - DREA Not a market Sale" priced far above assessment.
    # Why (2026-11-21): DC's tax office coded the press-report sale "Unusual";
    # Arlington's nearest equivalent is N, set by the Department of Real Estate
    # Assessments after review. The comps screen above drops N as non-market,
    # so these were never looked at. Same explanation rules as the comps screen.
    nm = []
    for s in recent:
        if (s.get("salesTypeCode") or "").strip() != "N":
            continue
        rpc, yr = s["realEstatePropertyCode"], s["saleDate"][:4]
        doc = (s.get("landRecordDocumentNbr") or "").strip()
        a = A[rpc].get(yr, 0)
        if not a or s["saleAmt"] < N_RATIO * a or (doc and doc_count[doc] > 1):
            continue
        p = P.get(rpc) or {}
        r = {"rpc": rpc, "date": s["saleDate"][:10], "price": s["saleAmt"], "assessed_jan1": a,
             "ratio": round(s["saleAmt"] / a, 2), "class": p.get("propertyClassTypeDsc"),
             "year_built": p.get("propertyYearBuilt"), "address": p.get("propertyStreetNbrNameText")}
        prior = [h for h in sorted(hist[rpc]) if h[0] < r["date"]]
        yb = r["year_built"] or 0
        if prior:
            pd, pp, _ = prior[-1]
            yrs = (date.fromisoformat(r["date"]) - date.fromisoformat(pd)).days / 365.25
            cagr = (r["price"] / pp) ** (1 / yrs) - 1 if yrs > 0 else None
            r.update(prev_date=pd, prev_price=pp, cagr=round(cagr, 4) if cagr is not None else None)
        if prior and pd > "1901" and yrs >= MIN_YEARS and cagr is not None and cagr <= MAX_CAGR:
            r["explained"] = "consistent with own sale history"
        elif prior and pd > "1901" and yb > int(pd[:4]):
            r["explained"] = f"rebuilt since previous sale (built {yb})"
        elif yb >= int(yr) - 1:
            r["explained"] = f"new construction (built {yb})"
        else:
            lo = f"{int(yr) - 2}{r['date'][4:]}"
            hits = [q for q in permits(rpc) if lo <= (q.get("issuedDate") or "")[:10] <= r["date"]
                    and (q.get("permitTypeCode") in CONSTRUCTION_TYPES or q.get("permitSubTypeCode") in CONSTRUCTION_SUBTYPES)]
            r["permits_in_window"] = [((q.get("issuedDate") or "")[:10], q.get("permitTypeCode"), q.get("permitSubTypeCode"),
                                       (q.get("permitDescriptionText") or "")[:120]) for q in hits]
            r["explained"] = "construction permit in the two years before the sale" if hits else None
        nm.append(r)

    off_mkt = [r for r in rows if r["code"] == "P"]
    report.update(house_sales_with_area=sum(1 for r in rows if r["house"] and r["sqft"]),
                  house_sales_with_enough_comps=sum(1 for r in rows if r.get("n_comps", 0) >= MIN_COMPS),
                  house_candidates=len(cands),
                  candidates_explained=sum(1 for r in cands if r["explained"]),
                  county_coded_not_listed=len(off_mkt),
                  assessor_not_market_n=sum(1 for s in recent if (s.get("salesTypeCode") or "").strip() == "N"),
                  assessor_not_market_high=len(nm),
                  assessor_not_market_high_explained=sum(1 for r in nm if r["explained"]))
    json.dump({"report": report, "candidates": cands, "county_coded_not_listed": off_mkt, "assessor_not_market_high": nm},
              open(os.path.join(CACHE, "screen.json"), "w"), indent=1)
    print(json.dumps(report, indent=1))
    print("\nComps-screen house candidates NOT explained (by gap over comps median):")
    for r in sorted([r for r in cands if not r["explained"]], key=lambda r: -(r["price"] - r["comps_median"])):
        prev = f"prev {r['prev_date']} ${r['prev_price']:,.0f}" if r.get("prev_date") else "no prior sale"
        print(f"  {r['date']} ${r['price']:>10,.0f}  comps median ${r['comps_median']:>10,.0f} (n={r['n_comps']}, {r['n_higher']} higher)"
              f"  $/sf x{r['ppsf_mult']}  code={r['code']}  assessed ${r['assessed_jan1']:,.0f}  {prev}  {r['address']}")
    print(f"\nAssessor-coded 'not a market sale' (N) at >= {N_RATIO}x assessment, NOT explained:")
    for r in sorted([r for r in nm if not r["explained"]], key=lambda r: -r["ratio"]):
        prev = f"prev {r['prev_date']} ${r['prev_price']:,.0f}" if r.get("prev_date") else "no prior sale"
        print(f"  {r['date']} ${r['price']:>10,.0f} x{r['ratio']} vs ${r['assessed_jan1']:,.0f}  {r['class']}  built {r['year_built']}  {prev}  {r['address']}")
    print("\nCounty-coded 'not listed MLS' sales with price far above assessment (ratio >= 1.5):")
    for r in sorted([r for r in off_mkt if r["ratio"] and r["ratio"] >= 1.5], key=lambda r: -r["ratio"]):
        print(f"  {r['date']} ${r['price']:>10,.0f} vs assessed ${r['assessed_jan1']:>10,.0f} x{r['ratio']:.2f}  n={len(r['rpcs'])}  {r['class']}  {r['address']}")


if __name__ == "__main__":
    main()
