"""
Wider candidate screen for "sold far above what anything comparable fetched",
with renovations filtered out up front by DC building permits.

Why (2026-11-21): the first comps screen (0 comparables at/above, $/sqft >= 1.5x)
gave 29 house sales; listing + permit checks cleared or explained all but two.
Most explained ones were flips with construction permits between purchase and
resale. So this screen loosens the comps test and then drops any sale with a
construction-type permit in the window before it, so the hand-run listing checks
go to sales whose price the public record doesn't already explain.

    python3 screen_candidates.py   ->  .cache/screen_v2.json, printed table

Comps test (houses: USECODE 011/012/013 with CAMA living area):
  qualified, non-multi-property sales in the same assessment neighborhood,
  within 183 days, living area within 25%, bedrooms within 1, at least 10 of them;
  candidate if at most MAX_HIGHER comparables sold at or above this price AND
  $/sqft >= PPSF_MULT x the comparables' median.
  (DC's CAMA living area undercounts listings by roughly 20-30% on the houses
  checked, so $/sqft is a ranking aid, not a measurement.)

Permit filter: drop the sale if any CONSTRUCTION permit (alteration, addition,
new building, raze, demolition) was issued for the SSL from PERMIT_LOOKBACK days
before the sale through the sale date. Trade-only permits (plumbing, mechanical,
electrical) and post cards don't count. Dropped sales are counted and listed in
the output, not silently removed.

No owner names are read or written.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pull import http_get, in_chunks  # noqa: E402

CACHE = os.path.join(HERE, ".cache")
PERMITS = "https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/DCRA/FeatureServer"
PERMIT_LAYERS = {2023: 15, 2024: 16, 2025: 17, 2026: 18}  # window never reaches before 2023
HOUSE = {"011", "012", "013"}
MIN_COMPS, MAX_HIGHER, PPSF_MULT = 10, 1, 1.3
PERMIT_LOOKBACK = 730


def q(url, where, fields):
    out, offset = [], 0
    while True:
        r = http_get(f"{url}/query", {"where": where, "outFields": fields, "returnGeometry": "false",
                                      "f": "json", "resultOffset": offset, "resultRecordCount": 2000})
        if "error" in r:
            raise RuntimeError(f"ArcGIS error {r['error']} ({where[:80]})")
        f = r.get("features", [])
        out += [x["attributes"] for x in f]
        if len(f) < 2000 and not r.get("exceededTransferLimit"):
            return out
        offset += len(f)


def construction_permits(ssls):
    """{ssl: [(issue_date, type, subtype, desc)]} for construction-type permits, 2023-2026."""
    out = defaultdict(list)
    for yr, lyr in PERMIT_LAYERS.items():
        for chunk in in_chunks(sorted(ssls), 150):
            inl = ",".join("'" + s.replace("'", "''") + "'" for s in chunk)
            for p in q(f"{PERMITS}/{lyr}", f"SSL IN ({inl}) AND PERMIT_TYPE_NAME = 'CONSTRUCTION'",
                       "SSL,ISSUE_DATE,PERMIT_TYPE_NAME,PERMIT_SUBTYPE_NAME,DESC_OF_WORK"):
                if p.get("ISSUE_DATE") is None:
                    continue
                d = datetime.fromtimestamp(p["ISSUE_DATE"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                out[p["SSL"]].append((d, p["PERMIT_TYPE_NAME"], p.get("PERMIT_SUBTYPE_NAME"),
                                      (p.get("DESC_OF_WORK") or "").strip()[:140]))
    return out


def main():
    d = json.load(open(os.path.join(CACHE, "flag_inputs.json")))
    it = {r["SSL"]: r for r in d["itspe"]}
    size = {}
    for c in d["res_cama"]:
        s = size.setdefault(c["SSL"], {"gba": 0.0, "bed": 0})
        s["gba"] += float(c.get("GBA") or 0)
        s["bed"] = max(s["bed"], int(c.get("BEDRM") or 0))
    sales = [s for s in d["sales"] if not (s.get("SALE_CODE") or "").startswith("M") and s["SSL"] in it
             and it[s["SSL"]].get("USECODE") in HOUSE and size.get(s["SSL"], {}).get("gba")]
    qual = defaultdict(list)
    for s in sales:
        if s["QUALIFIED"] == "Q":
            qual[it[s["SSL"]]["NBHD"]].append(s)
    checked = set()
    p = os.path.join(CACHE, "listing_checks.json")
    if os.path.exists(p):
        checked = {(e["ssl"], e["sale_date"]) for e in json.load(open(p))}

    cands, n_eval = [], 0
    for s in sales:
        me, d0 = size[s["SSL"]], date.fromisoformat(s["SALE_DATE"])
        comps = [c for c in qual[it[s["SSL"]]["NBHD"]] if c["SSL"] != s["SSL"]
                 and abs((date.fromisoformat(c["SALE_DATE"]) - d0).days) <= 183
                 and abs(size[c["SSL"]]["gba"] - me["gba"]) <= 0.25 * me["gba"]
                 and abs(size[c["SSL"]]["bed"] - me["bed"]) <= 1]
        if len(comps) < MIN_COMPS:
            continue
        n_eval += 1
        higher = sum(c["SALE_PRICE"] >= s["SALE_PRICE"] for c in comps)
        ppsf = statistics.median(c["SALE_PRICE"] / size[c["SSL"]]["gba"] for c in comps)
        mult = (s["SALE_PRICE"] / me["gba"]) / ppsf
        if higher <= MAX_HIGHER and mult >= PPSF_MULT:
            med = statistics.median(c["SALE_PRICE"] for c in comps)
            cands.append({"ssl": s["SSL"], "date": s["SALE_DATE"], "price": s["SALE_PRICE"], "code": s["SALE_CODE"],
                          "q": s["QUALIFIED"], "n_comps": len(comps), "n_higher": higher, "ppsf_mult": round(mult, 2),
                          "comps_median": med, "gap_vs_median": s["SALE_PRICE"] - med,
                          "address": it[s["SSL"]]["PREMISEADD"], "nbhd": it[s["SSL"]]["NBHDNAME"],
                          "already_checked": (s["SSL"], s["SALE_DATE"]) in checked})
    perms = construction_permits({c["ssl"] for c in cands})
    kept, dropped = [], []
    for c in cands:
        lo = (date.fromisoformat(c["date"]) - timedelta(days=PERMIT_LOOKBACK)).isoformat()
        win = [p for p in perms.get(c["ssl"], []) if lo <= p[0] <= c["date"]]
        c["construction_permits_in_window"] = win
        (dropped if win else kept).append(c)
    kept.sort(key=lambda c: -c["gap_vs_median"])
    out = {"params": {"MIN_COMPS": MIN_COMPS, "MAX_HIGHER": MAX_HIGHER, "PPSF_MULT": PPSF_MULT,
                      "PERMIT_LOOKBACK_DAYS": PERMIT_LOOKBACK},
           "house_sales_with_enough_comps": n_eval, "candidates": len(cands),
           "dropped_construction_permit": len(dropped), "kept": kept, "dropped": dropped}
    json.dump(out, open(os.path.join(CACHE, "screen_v2.json"), "w"), indent=1)
    print(f"house sales evaluated: {n_eval}; candidates: {len(cands)}; dropped for construction permits: "
          f"{len(dropped)}; kept: {len(kept)} ({sum(c['already_checked'] for c in kept)} already listing-checked)")
    for c in kept:
        flag = "checked" if c["already_checked"] else "NEW"
        print(f"  {flag:7} {c['date']} ${c['price']:>11,.0f}  comps median ${c['comps_median']:>10,.0f} (n={c['n_comps']}, "
              f"{c['n_higher']} higher)  $/sf x{c['ppsf_mult']}  {c['q']} {c['code']}  {c['address'].split(' WASHINGTON')[0]} [{c['nbhd']}]")


if __name__ == "__main__":
    main()
