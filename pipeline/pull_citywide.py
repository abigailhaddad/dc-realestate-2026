"""
Pull citywide parcel + ITSPE + CAMA data, joined to neighborhood clusters,
for the one-off slide visualizations.

Outputs to ../data/:
    citywide_parcels.json  — every parcel with lat/lon, use category, year built
    citywide_owners.json   — owner-aggregated counts + assessed value
    citywide_use_mix.json  — use category × cluster breakdown
    citywide_clusters.json — per-cluster use-mix + tax-exempt share

Runs in ~5-10 minutes.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import defaultdict

FOREIGN_RE = re.compile(
    r"^(GOVERNMENT OF|EMBASSY|FEDERAL REPUBLIC OF|ROYAL|KINGDOM OF|"
    r"REPUBLIC OF|DEMOCRATIC REPUBLIC|ARAB REPUBLIC|AMBASSADOR)",
    re.IGNORECASE,
)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pull import (  # noqa: E402
    arcgis_query, in_chunks, http_get, TAX_LOTS, ITSPE,
    COMMERCIAL_CAMA, RESIDENTIAL_CAMA, USECODE, categorize_use,
)
from analyze import fetch_cluster_polygons, RESIDENTIAL, COMMERCIAL  # noqa: E402

OUT_DIR = os.path.join(HERE, "..", "data")


def point_in_polygon(lat, lon, rings):
    if not rings:
        return False
    ring = rings[0]
    inside, n, j = False, len(ring), len(ring) - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


# Tax-exempt-ish use codes — use codes typically class-3-or-4 (non-private).
TAX_EXEMPT_CODES = {
    "081", "082", "083", "084", "085", "086", "087", "088", "089",   # special purpose
    "061",                                                            # banks/financial (rarely)
}


def load_usecode_lookup():
    rows = arcgis_query(USECODE, outFields="CODE,DESCRIPTION")
    return {r["CODE"]: r.get("DESCRIPTION", "") for r in rows}


def pull_all_tax_lot_geometries():
    """Pull every tax lot. Return (centroids_by_ssl, rings_by_ssl)."""
    print("[parcels] Pulling all tax lot polygons + centroids…")
    params = {
        "where": "1=1",
        "outFields": "SSL",
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "json",
        "resultRecordCount": 2000,
    }
    centroids = {}
    polygons = {}
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
            outer = rings[0]
            xs = [p[0] for p in outer]
            ys = [p[1] for p in outer]
            centroids[ssl] = (round(sum(ys) / len(ys), 6), round(sum(xs) / len(xs), 6))
            # Round to 6 decimals (~10 cm) and keep only the outer ring for size.
            polygons[ssl] = [[round(p[0], 6), round(p[1], 6)] for p in outer]
        if len(feats) < params["resultRecordCount"]:
            break
        offset += len(feats)
        if offset % 10000 == 0:
            print(f"  …{offset} parcels pulled, {len(centroids):,} kept")
    print(f"  Got {len(centroids):,} centroids + polygons")
    return centroids, polygons


def pull_all_itspe():
    print("[itspe] Pulling all 221k ITSPE rows (~3 min)…")
    rows = arcgis_query(
        ITSPE,
        where="1=1",
        outFields="SSL,USECODE,PREMISEADD,OWNERNAME,LANDAREA,NEWTOTAL",
    )
    print(f"  Got {len(rows):,} ITSPE rows")
    return rows


def pull_all_cama_year_built():
    """Pull AYB (year built) from both commercial + residential CAMA tables."""
    out = {}
    for url, name in [(RESIDENTIAL_CAMA, "residential"), (COMMERCIAL_CAMA, "commercial")]:
        print(f"[cama] Pulling AYB from {name}…")
        rows = arcgis_query(url, outFields="SSL,AYB")
        for r in rows:
            ssl = r.get("SSL")
            ayb = r.get("AYB")
            if ssl and ayb and 1700 <= ayb <= 2030:
                out[ssl] = int(ayb)
        print(f"  Running total: {len(out):,} parcels with AYB")
    return out


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)

    use_lookup = load_usecode_lookup()
    centroids, polygons = pull_all_tax_lot_geometries()
    itspe = pull_all_itspe()
    aybs = pull_all_cama_year_built()
    clusters = fetch_cluster_polygons()
    print(f"  {len(clusters)} cluster polygons")

    # Assign each parcel to a cluster (slow O(N*C) but C=46, fine).
    print("[join] Spatially joining parcels to clusters…")
    parcel_cluster = {}
    for ssl, (lat, lon) in centroids.items():
        for c in clusters:
            if point_in_polygon(lat, lon, c["rings"]):
                parcel_cluster[ssl] = (c["cluster_num"], c["cluster_name"])
                break
    print(f"  Joined {len(parcel_cluster):,} parcels to clusters")

    # --- Build parcels JSON for the year-built map ---
    # Compact format: [lat, lon, year_built, category_index]
    cats = ["single_family", "condo", "multifamily", "office", "retail",
            "hotel_lodging", "industrial", "commercial_other", "institutional",
            "vacant", "other"]
    cat_index = {c: i for i, c in enumerate(cats)}

    parcels_compact = []
    for r in itspe:
        ssl = r.get("SSL")
        use_code = r.get("USECODE") or ""
        cat = categorize_use(use_code)
        ll = centroids.get(ssl)
        ayb = aybs.get(ssl)
        if not ll:
            continue
        parcels_compact.append([ll[0], ll[1], ayb, cat_index.get(cat, 10)])
    print(f"[parcels] Compact parcel records: {len(parcels_compact):,}")

    # --- Top owners ---
    owner_counts = defaultdict(lambda: {"count": 0, "assessed": 0})
    for r in itspe:
        owner = (r.get("OWNERNAME") or "").strip()
        if not owner:
            continue
        owner_counts[owner]["count"] += 1
        owner_counts[owner]["assessed"] += r.get("NEWTOTAL") or 0
    top_owners = sorted(
        ({"owner": k, "parcels": v["count"], "assessed_total": v["assessed"]}
         for k, v in owner_counts.items()),
        key=lambda r: r["parcels"], reverse=True,
    )[:50]
    print(f"[owners] Top owner has {top_owners[0]['parcels']} parcels")

    # --- Use mix ---
    # Two bases, both useful:
    #   "count" = every ITSPE row (each condo unit gets its own row)
    #   "parcels" / "land_sqft" / "assessed" = one row per tax lot — what
    #     the parcel map actually shows. Computed by deduping ITSPE by SSL,
    #     first row wins, so each tax lot is counted exactly once.
    use_mix_totals = defaultdict(lambda: {"count": 0, "parcels": 0, "land_sqft": 0, "assessed": 0})
    use_mix_by_cluster = defaultdict(lambda: defaultdict(int))
    cluster_assessed_total = defaultdict(int)
    cluster_assessed_exempt = defaultdict(int)
    # parcel_cats: only SSLs that correspond to a TAX-LOT polygon. DC's CAMA
    # gives each condo unit its own ITSPE SSL too, so we filter to the ~30K
    # ITSPE SSLs that also appear in the Tax Lots layer.
    parcel_cats = {}
    for r in itspe:
        ssl = r.get("SSL")
        use_code = r.get("USECODE") or ""
        cat = categorize_use(use_code)
        assessed = r.get("NEWTOTAL") or 0
        use_mix_totals[cat]["count"] += 1
        if ssl and ssl in centroids and ssl not in parcel_cats:
            parcel_cats[ssl] = cat
            use_mix_totals[cat]["parcels"] += 1
            use_mix_totals[cat]["land_sqft"] += (r.get("LANDAREA") or 0)
            use_mix_totals[cat]["assessed"] += assessed
        cluster_info = parcel_cluster.get(ssl)
        if cluster_info:
            cnum, cname = cluster_info
            if ssl in parcel_cats and parcel_cats[ssl] == cat:
                use_mix_by_cluster[cnum][cat] += 1
            cluster_assessed_total[cnum] += assessed
            if use_code in TAX_EXEMPT_CODES:
                cluster_assessed_exempt[cnum] += assessed

    total_count = sum(t["count"] for t in use_mix_totals.values())
    total_parcels = sum(t["parcels"] for t in use_mix_totals.values())
    total_land = sum(t["land_sqft"] for t in use_mix_totals.values())
    total_assessed = sum(t["assessed"] for t in use_mix_totals.values())
    use_mix = sorted(
        [
            {
                "category": cat,
                "count": t["count"],
                "share_count": t["count"] / total_count if total_count else 0,
                "parcels": t["parcels"],
                "share_parcels": t["parcels"] / total_parcels if total_parcels else 0,
                "land_sqft": int(t["land_sqft"]),
                "share_land": t["land_sqft"] / total_land if total_land else 0,
                "assessed": int(t["assessed"]),
                "share_assessed": t["assessed"] / total_assessed if total_assessed else 0,
            }
            for cat, t in use_mix_totals.items()
        ],
        key=lambda r: -r["parcels"],
    )
    print(f"[use_mix] Top category: {use_mix[0]['category']} = {use_mix[0]['count']:,}")

    # Citywide clusters JSON with tax-exempt + use-mix per cluster.
    cluster_lookup = {c["cluster_num"]: c for c in clusters}
    citywide_clusters = []
    for cnum in sorted(use_mix_by_cluster.keys()):
        c = cluster_lookup.get(cnum, {})
        total_a = cluster_assessed_total[cnum]
        exempt_a = cluster_assessed_exempt[cnum]
        citywide_clusters.append({
            "cluster_num": cnum,
            "cluster_name": c.get("cluster_name", ""),
            "rings": c.get("rings", []),
            "use_mix": dict(use_mix_by_cluster[cnum]),
            "parcels": sum(use_mix_by_cluster[cnum].values()),
            "assessed_total": total_a,
            "assessed_exempt": exempt_a,
            "exempt_share": exempt_a / total_a if total_a else 0,
        })
    print(f"[clusters] {len(citywide_clusters)} cluster summaries")

    def write(name, obj):
        out = os.path.join(OUT_DIR, name)
        with open(out, "w") as fh:
            json.dump(obj, fh, separators=(",", ":"))
        sz = os.path.getsize(out)
        print(f"  Wrote {name} ({sz:,} bytes)")

    # Foreign-government owners: regex-filter the full owner_counts map, not the top-50.
    foreign = [
        {"owner": k, "parcels": v["count"], "assessed_total": v["assessed"]}
        for k, v in owner_counts.items()
        if FOREIGN_RE.match(k)
    ]
    foreign.sort(key=lambda r: r["assessed_total"], reverse=True)
    print(f"[foreign] {len(foreign)} foreign-government owners")

    # Per-parcel foreign-gov data with centroids, for the flag map.
    foreign_owner_names = {r["owner"] for r in foreign}
    foreign_parcels = []
    for r in itspe:
        owner = (r.get("OWNERNAME") or "").strip()
        ssl = r.get("SSL")
        if owner in foreign_owner_names and ssl in centroids:
            lat, lon = centroids[ssl]
            foreign_parcels.append({
                "owner": owner,
                "lat": lat,
                "lon": lon,
                "assessed": r.get("NEWTOTAL") or 0,
                "address": r.get("PREMISEADD") or "",
            })
    print(f"[foreign_parcels] {len(foreign_parcels)} parcels with centroids")

    write("citywide_parcels.json", {"categories": cats, "parcels": parcels_compact})

    # --- Parcel records keyed by SSL: category + year built + lot area + centroid ---
    # Compact format per row: [category_index, year_built_or_null, land_area, lat, lon]
    # One row per parcel (deduped from ITSPE which has multiple rows per condo lot).
    ssl_to_cat = {}
    ssl_to_land = {}
    for r in itspe:
        ssl = r.get("SSL")
        if not ssl or ssl in ssl_to_cat:
            continue
        cat = categorize_use(r.get("USECODE") or "")
        ssl_to_cat[ssl] = cat_index.get(cat, 10)
        ssl_to_land[ssl] = int(r.get("LANDAREA") or 0)

    parcel_dots = []
    for ssl, (lat, lon) in centroids.items():
        if ssl in ssl_to_cat:
            parcel_dots.append([
                ssl_to_cat[ssl],
                aybs.get(ssl),
                ssl_to_land.get(ssl, 0),
                lat,
                lon,
            ])
    print(f"[shapes] {len(parcel_dots):,} parcel records (category + year + area + centroid)")
    write("citywide_parcel_shapes.json", {"categories": cats, "parcels": parcel_dots})
    write("citywide_owners.json", top_owners)
    write("citywide_foreign.json", foreign)
    write("citywide_foreign_parcels.json", foreign_parcels)
    write("citywide_use_mix.json", use_mix)
    write("citywide_clusters.json", citywide_clusters)

    print(f"\nDone in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
