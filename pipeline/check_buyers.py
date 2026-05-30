"""
Quick diagnostic: do more residential sales go to LLCs / corporations over time?

We can't see the buyer for every historical sale (DC's CAMA Property Sales
table doesn't expose grantee names cleanly). What we *can* see is the
current owner per parcel via ITSPE, and ITSPE also reports the most-recent
qualified sale date. So for every parcel where the current owner acquired
it in year Y, we know the buyer that acquired it.

This is biased toward parcels that haven't traded since — but for recent
years (2024-2026) the bias is minimal since those owners are still current.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pull import (  # noqa: E402
    arcgis_query, in_chunks, ITSPE, fmt_date,
)

CORP = re.compile(
    r"\b(LLC|L\.L\.C\.|L L C|LP|L\.P\.|INC|CORP|COMPANY|"
    r"HOLDINGS|TRUST|TRUSTEES|PROPERTIES|INVESTMENTS|"
    r"PARTNERSHIP|LIMITED|GROUP|VENTURES|REALTY|CAPITAL|"
    r"FUND|ASSOCIATES)\b",
    re.IGNORECASE,
)


def main():
    src = os.path.join(HERE, "..", "data", "sales.json")
    print(f"Reading {src}…")
    sales = json.load(open(src))
    # Restrict to residential
    res = [s for s in sales if s.get("use_category") in ("single_family", "condo", "multifamily")]
    unique_ssls = sorted({s["SSL"] if "SSL" in s else s.get("ssl") for s in res if s.get("ssl") or s.get("SSL")})
    print(f"{len(res):,} residential sales over {len(unique_ssls):,} unique parcels")

    print("Pulling ITSPE OWNERNAME + SALEDATE for those parcels…")
    itspe = []
    for chunk in in_chunks(unique_ssls, 400):
        in_list = ",".join(f"'{s}'" for s in chunk)
        itspe.extend(arcgis_query(
            ITSPE,
            where=f"SSL IN ({in_list})",
            outFields="SSL,OWNERNAME,SALEDATE,SALEPRICE",
        ))
    print(f"Got ITSPE for {len(itspe):,} parcels")

    by_year = defaultdict(lambda: {"corp": 0, "indiv": 0})
    for r in itspe:
        owner = (r.get("OWNERNAME") or "").strip()
        sd = fmt_date(r.get("SALEDATE"))
        if not owner or not sd or sd < "2020-01-01":
            continue
        y = sd[:4]
        if CORP.search(owner):
            by_year[y]["corp"] += 1
        else:
            by_year[y]["indiv"] += 1

    print()
    print(f"{'Year':<6} {'Corp':>7} {'Indiv':>7} {'Total':>7} {'Corp %':>8}")
    print("-" * 40)
    for y in sorted(by_year):
        r = by_year[y]
        tot = r["corp"] + r["indiv"]
        pct = 100 * r["corp"] / tot if tot else 0
        print(f"{y:<6} {r['corp']:>7,} {r['indiv']:>7,} {tot:>7,} {pct:>7.1f}%")


if __name__ == "__main__":
    main()
