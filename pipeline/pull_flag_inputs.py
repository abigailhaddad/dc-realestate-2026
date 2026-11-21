"""
Pull the inputs for the "sold far above expected" flag (flag_overpriced.py).

What it pulls, for every sale recorded since SALES_CUTOFF (ALL qualification
codes, not just 'Q' -- see below):

  - Property Sales (layer 57): SSL, date, price, QUALIFIED, SALE_CODE.
    No buyer or seller names are pulled: the flag is about a sale's price,
    never about who bought or sold. (The layer has no name field anyway:
    SALE_CURR_OWNER is a "1"/"0" string meaning "this sale's buyer is the
    current owner", checked 2026-11-21.)
  - ITSPE (layer 53): use code, address, assessment neighborhood, land area,
    and both published assessments (OLDTOTAL / NEWTOTAL; see below).
  - Residential CAMA (layer 25): size and features of the house.
  - USECODE lookup (layer 54): CODE -> DESCRIPTION, so flag_overpriced.py can
    tell a condo from a condo parking space (see its prop_class()). Written to
    pipeline/.cache/usecodes.json; nothing else in this pipeline produced that
    file before 2026-11-21, so flag_overpriced.py would fail on a clean clone.

Why every qualification code: DC's 'Q' (qualified / arm's-length) code is
assigned by OTR after review. An off-market sale between LLCs can plausibly be
coded unqualified, and the existing pull.py would drop it before anyone looks.
flag_overpriced.py decides what to do with each code and reports the counts.

Why only since 2025: the API publishes just two assessments per parcel.
As of the 2026-11-19 extract, CY1YEAR = 2026, so OLDTOTAL = tax year 2026
(valued as of 2025-01-01) and NEWTOTAL = tax year 2027 (valued as of
2026-01-01). A sale can only be compared with an assessment valued before it,
which these two cover for sales in 2025 and 2026.

Unlike pull.py's arcgis_query, every query here raises on an ArcGIS error
response. (pull.py's residential CAMA request names a field the layer doesn't
have, LIVING_GBA; the server answers with an error, the helper reads that as
"no rows", and building_sqft ended up blank on ~all residential sales.)

Output: pipeline/.cache/flag_inputs.json (gitignored; regenerable).
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pull import http_get, arcgis_query, in_chunks, ITSPE, PROPERTY_SALES, RESIDENTIAL_CAMA, USECODE  # noqa: E402

CACHE_DIR = os.path.join(HERE, ".cache")
OUT = os.path.join(CACHE_DIR, "flag_inputs.json")
USECODES_OUT = os.path.join(CACHE_DIR, "usecodes.json")
SALES_CUTOFF = "2025-01-01"

SALES_FIELDS = "SSL,SALE_DATE,SALE_PRICE,QUALIFIED,SALE_CODE"
ITSPE_FIELDS = ("SSL,USECODE,PREMISEADD,NBHD,NBHDNAME,SUBNBHD,LANDAREA,PROPTYPE,"
                "OLDTOTAL,NEWTOTAL,CY1YEAR,EXTRACTDAT")
RES_FIELDS = ("SSL,BLDG_NUM,GBA,BEDRM,BATHRM,HF_BATHRM,ROOMS,AYB,YR_RMDL,EYB,STORIES,"
              "STRUCT_D,STYLE_D,GRADE_D,CNDTN_D,FIREPLACES,NUM_UNITS,USECODE,LANDAREA")


def query_all(layer_url, where, fields):
    """Paged ArcGIS query that fails loudly on an error response."""
    out, offset, page_size = [], 0, 2000
    while True:
        resp = http_get(f"{layer_url}/query", {
            "where": where, "outFields": fields, "returnGeometry": "false",
            "f": "json", "resultRecordCount": page_size, "resultOffset": offset,
            "orderByFields": "OBJECTID",
        })
        if "error" in resp:
            raise RuntimeError(f"ArcGIS error from {layer_url}: {resp['error']} (where={where[:120]})")
        feats = resp.get("features", [])
        out.extend(f["attributes"] for f in feats)
        if len(feats) < page_size and not resp.get("exceededTransferLimit"):
            break
        if not feats:
            break
        offset += len(feats)
    return out


def by_ssl(layer_url, ssls, fields):
    out = []
    for chunk in in_chunks(sorted(ssls), 300):
        in_list = ",".join(f"'{s}'" for s in chunk)
        out.extend(query_all(layer_url, f"SSL IN ({in_list})", fields))
    return out


def iso(ms):
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def main():
    t0 = time.time()
    os.makedirs(CACHE_DIR, exist_ok=True)

    where = f"SALE_DATE >= DATE '{SALES_CUTOFF}' AND SALE_PRICE > 0"
    print(f"[1/4] sales: {where}")
    sales = query_all(PROPERTY_SALES, where, SALES_FIELDS)
    for s in sales:
        s["SALE_DATE"] = iso(s["SALE_DATE"])
    print(f"      {len(sales):,} rows")

    ssls = {s["SSL"] for s in sales if s.get("SSL")}
    print(f"[2/4] ITSPE for {len(ssls):,} parcels")
    itspe = by_ssl(ITSPE, ssls, ITSPE_FIELDS)
    for r in itspe:
        r["EXTRACTDAT"] = iso(r.get("EXTRACTDAT"))
    print(f"      {len(itspe):,} rows")

    print(f"[3/4] residential CAMA")
    res = by_ssl(RESIDENTIAL_CAMA, ssls, RES_FIELDS)
    print(f"      {len(res):,} rows")

    print(f"[4/4] USECODE lookup (for flag_overpriced.py's prop_class)")
    usecode_rows = arcgis_query(USECODE, outFields="CODE,DESCRIPTION")
    usecodes = {r["CODE"]: r.get("DESCRIPTION", "") for r in usecode_rows}
    with open(USECODES_OUT, "w") as fh:
        json.dump(usecodes, fh)
    print(f"      {len(usecodes):,} codes -> {USECODES_OUT}")

    with open(OUT, "w") as fh:
        json.dump({
            "pulled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sales_cutoff": SALES_CUTOFF,
            "sales": sales, "itspe": itspe, "res_cama": res,
        }, fh)
    print(f"wrote {OUT} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
