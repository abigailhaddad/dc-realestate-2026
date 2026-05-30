"""
Pull all qualified DC property sales from 2020-01-01 forward, plus per-parcel
metadata (use code, address, neighborhood cluster, building size).

Outputs `../data/sales.json` for the Next.js app to consume.

Data source: DC Office of Tax & Revenue, via ArcGIS REST on maps2.dcgis.dc.gov.
No API key required.

Roughly ~5 minutes for a full citywide pull.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "data")

BASE = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA"
PROPERTY = f"{BASE}/Property_and_Land_WebMercator/FeatureServer"
ADMIN = f"{BASE}/Administrative_Other_Boundaries_WebMercator/MapServer"

PROPERTY_SALES = f"{PROPERTY}/57"      # full sale history
ITSPE = f"{PROPERTY}/53"               # one row per parcel — use code, address, owner
COMMERCIAL_CAMA = f"{PROPERTY}/23"     # commercial building details (LIVING_GBA, AYB)
RESIDENTIAL_CAMA = f"{PROPERTY}/25"    # residential building details
USECODE = f"{PROPERTY}/54"             # use code lookup
TAX_LOTS = f"{PROPERTY}/39"            # parcel polygons (for centroids + cluster join)
CLUSTERS = f"{ADMIN}/17"               # labeled neighborhood clusters

# Qualified arms-length sales only. Excludes $0 transfers, intra-family,
# trustee transfers, etc.
SALES_CUTOFF = "2020-01-01"


def http_get(url, params):
    qs = urllib.parse.urlencode(params)
    full = f"{url}?{qs}"
    if len(full) < 7000:
        req = urllib.request.Request(full, headers={"User-Agent": "dc-realestate-2026/0.1"})
    else:
        req = urllib.request.Request(
            url, data=qs.encode(),
            headers={
                "User-Agent": "dc-realestate-2026/0.1",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def arcgis_query(layer_url, **params):
    params.setdefault("f", "json")
    params.setdefault("where", "1=1")
    params.setdefault("outFields", "*")
    params.setdefault("returnGeometry", "false")
    params.setdefault("resultRecordCount", 2000)
    out, offset = [], 0
    while True:
        page = dict(params, resultOffset=offset)
        resp = http_get(f"{layer_url}/query", page)
        feats = resp.get("features", [])
        if not feats:
            break
        for f in feats:
            attrs = dict(f["attributes"])
            if f.get("geometry") is not None:
                attrs["__geometry__"] = f["geometry"]
            out.append(attrs)
        if len(feats) < params["resultRecordCount"]:
            break
        offset += len(feats)
    return out


def in_chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def fmt_date(ms):
    if ms is None:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def pull_qualified_sales():
    """Every qualified, non-zero sale citywide since SALES_CUTOFF."""
    where = (
        f"SALE_DATE >= DATE '{SALES_CUTOFF}' "
        f"AND SALE_PRICE > 0 "
        f"AND QUALIFIED = 'Q'"
    )
    print(f"  query: {where}")
    rows = arcgis_query(
        PROPERTY_SALES,
        where=where,
        outFields="SSL,SALE_DATE,SALE_PRICE,QUALIFIED,SALE_CODE,SALE_CURR_OWNER",
    )
    return rows


def pull_itspe_for_ssls(ssls):
    out = []
    for chunk in in_chunks(ssls, 400):
        in_list = ",".join(f"'{s}'" for s in chunk)
        where = f"SSL IN ({in_list})"
        out.extend(arcgis_query(
            ITSPE, where=where,
            outFields="SSL,USECODE,PREMISEADD,OWNERNAME,LANDAREA,NBHD,NEWTOTAL",
        ))
    return out


def pull_cama_for_ssls(ssls, table_url, fields):
    out = []
    for chunk in in_chunks(ssls, 400):
        in_list = ",".join(f"'{s}'" for s in chunk)
        where = f"SSL IN ({in_list})"
        out.extend(arcgis_query(table_url, where=where, outFields=fields))
    return out


def load_usecode_lookup():
    rows = arcgis_query(USECODE, outFields="CODE,DESCRIPTION")
    return {r["CODE"]: r.get("DESCRIPTION", "") for r in rows}


def pull_cluster_geometries():
    """Return list of (cluster_num, name, geometry_polygon) for spatial joining."""
    rows = arcgis_query(CLUSTERS, outFields="NAME,NBH_NAMES", returnGeometry="true", outSR=4326)
    out = []
    for r in rows:
        nm = r.get("NAME", "")
        if not nm.startswith("Cluster"):
            continue
        try:
            cnum = int(nm.split()[-1])
        except (ValueError, IndexError):
            continue
        geom = r.get("__geometry__")
        if not geom or not geom.get("rings"):
            continue
        out.append({"num": cnum, "name": r.get("NBH_NAMES", ""), "geom": geom})
    return out


def point_in_polygon(lat, lon, rings):
    """Ray-casting on the outer ring only — adequate for compact clusters."""
    if not rings:
        return False
    ring = rings[0]
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def categorize_use(code):
    """Bucket DC use codes into report-friendly categories."""
    if not code:
        return "other"
    if code in {"011", "012", "013", "014", "015", "019"}:
        return "single_family"
    if code in {"016", "017", "018", "116", "117", "216", "217", "316", "416", "417", "516"}:
        return "condo"
    if code in {"021", "022", "023", "024", "025", "026", "027", "028", "029"}:
        return "multifamily"
    if code in {"031", "032", "033", "035", "036", "037", "038", "039"}:
        return "hotel_lodging"
    if code in {"041", "042", "043", "044", "045", "046", "047", "048", "049"}:
        return "retail"
    if code in {"051", "052", "053", "056", "057", "058", "059"}:
        return "office"
    if code in {"061", "062", "063", "064", "065", "066", "067", "068", "069"}:
        return "commercial_other"
    if code in {"071", "072", "073", "074", "075", "076", "078", "079"}:
        return "industrial"
    if code in {"081", "082", "083", "084", "085", "086", "087", "088", "089"}:
        return "institutional"
    if code in {"091", "092", "093", "094", "095", "096", "097", "191", "192", "193", "194", "195", "196", "197"}:
        return "vacant"
    return "other"


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)

    print("[1/6] Pulling qualified sales since 2020…")
    sales = pull_qualified_sales()
    print(f"      {len(sales):,} qualified sales records")
    if not sales:
        sys.exit("No sales pulled — check the endpoint or date filter.")

    print("[2/6] Loading use-code lookup + cluster polygons…")
    use_lookup = load_usecode_lookup()
    clusters = pull_cluster_geometries()
    print(f"      {len(clusters)} clusters loaded")

    unique_ssls = list({s["SSL"] for s in sales if s.get("SSL")})
    print(f"[3/6] Pulling ITSPE for {len(unique_ssls):,} unique parcels…")
    itspe_rows = pull_itspe_for_ssls(unique_ssls)
    itspe_by_ssl = {r["SSL"]: r for r in itspe_rows}
    print(f"      Got ITSPE for {len(itspe_by_ssl):,} parcels")

    print(f"[4/6] Pulling CAMA building details…")
    res_cama = pull_cama_for_ssls(
        unique_ssls, RESIDENTIAL_CAMA,
        "SSL,LIVING_GBA,AYB,YR_RMDL,NUM_UNITS,BEDRM",
    )
    com_cama = pull_cama_for_ssls(
        unique_ssls, COMMERCIAL_CAMA,
        "SSL,LIVING_GBA,AYB,YR_RMDL,NUM_UNITS",
    )
    cama_by_ssl = {}
    for r in res_cama + com_cama:
        ssl = r["SSL"]
        prior = cama_by_ssl.get(ssl)
        if prior is None or (r.get("LIVING_GBA") or 0) > (prior.get("LIVING_GBA") or 0):
            cama_by_ssl[ssl] = r
    print(f"      Got CAMA for {len(cama_by_ssl):,} parcels")

    print(f"[5/6] Pulling parcel centroids for cluster join…")
    centroids = {}
    for chunk in in_chunks(unique_ssls, 200):
        in_list = ",".join(f"'{s}'" for s in chunk)
        params = {
            "where": f"SSL IN ({in_list})",
            "outFields": "SSL",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "json",
            "resultRecordCount": 2000,
        }
        offset = 0
        while True:
            page = dict(params, resultOffset=offset)
            resp = http_get(f"{TAX_LOTS}/query", page)
            feats = resp.get("features", [])
            if not feats:
                break
            for ft in feats:
                ssl = ft["attributes"].get("SSL")
                geom = ft.get("geometry") or {}
                rings = geom.get("rings") or []
                if not ssl or not rings:
                    continue
                pts = rings[0]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                centroids[ssl] = (sum(ys) / len(ys), sum(xs) / len(xs))
            if len(feats) < params["resultRecordCount"]:
                break
            offset += len(feats)
    print(f"      Got centroids for {len(centroids):,} parcels")

    print(f"[6/6] Joining everything + writing JSON…")
    out_rows = []
    for s in sales:
        ssl = s.get("SSL")
        itspe = itspe_by_ssl.get(ssl, {})
        cama = cama_by_ssl.get(ssl, {})
        use_code = itspe.get("USECODE") or ""
        lat, lon = centroids.get(ssl, (None, None))
        cluster_num = None
        cluster_name = ""
        if lat is not None and lon is not None:
            for c in clusters:
                if point_in_polygon(lat, lon, c["geom"]["rings"]):
                    cluster_num = c["num"]
                    cluster_name = c["name"]
                    break
        out_rows.append({
            "ssl": ssl,
            "sale_date": fmt_date(s.get("SALE_DATE")),
            "sale_price": s.get("SALE_PRICE") or 0,
            "sale_code": s.get("SALE_CODE") or "",
            "buyer": s.get("SALE_CURR_OWNER") or "",
            "use_code": use_code,
            "use_description": use_lookup.get(use_code, ""),
            "use_category": categorize_use(use_code),
            "address": itspe.get("PREMISEADD") or "",
            "land_area": itspe.get("LANDAREA"),
            "building_sqft": cama.get("LIVING_GBA"),
            "year_built": cama.get("AYB"),
            "num_units": cama.get("NUM_UNITS"),
            "current_assessment": itspe.get("NEWTOTAL"),
            "cluster_num": cluster_num,
            "cluster_name": cluster_name,
            "lat": lat,
            "lon": lon,
        })

    out_rows.sort(key=lambda r: r["sale_date"], reverse=True)

    out_path = os.path.join(OUT_DIR, "sales.json")
    with open(out_path, "w") as fh:
        json.dump(out_rows, fh, separators=(",", ":"))

    elapsed = time.time() - t0
    print(f"\nWrote {len(out_rows):,} sales → {out_path}")
    print(f"({elapsed:.1f}s elapsed)")


if __name__ == "__main__":
    main()
