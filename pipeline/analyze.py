"""
Aggregate the raw sales.json into small report-friendly JSON files
that the React app can load directly.

Inputs:  ../data/sales.json    (~18 MB, all qualified DC sales 2020+)
Outputs:
    ../data/monthly.json       — monthly sale count + median $ by use category
    ../data/by_use.json        — totals by use category (volume, median, change)
    ../data/by_cluster.json    — totals by neighborhood cluster
    ../data/summary.json       — headline numbers
    ../data/top_sales.json     — top 50 sales 2025-2026 YTD
"""
from __future__ import annotations

import json
import os
import statistics
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")

CLUSTERS_LAYER_URL = (
    "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/"
    "Administrative_Other_Boundaries_WebMercator/MapServer/17/query"
)


def fetch_cluster_polygons():
    """Pull DC neighborhood cluster polygons as GeoJSON-style rings."""
    params = urllib.parse.urlencode({
        "where": "1=1",
        "outFields": "NAME,NBH_NAMES",
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "json",
    })
    req = urllib.request.Request(
        f"{CLUSTERS_LAYER_URL}?{params}",
        headers={"User-Agent": "dc-realestate-2026/0.1"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    out = []
    for f in data.get("features", []):
        nm = f["attributes"].get("NAME", "")
        if not nm.startswith("Cluster"):
            continue
        try:
            cnum = int(nm.split()[-1])
        except (ValueError, IndexError):
            continue
        geom = f.get("geometry") or {}
        rings = geom.get("rings") or []
        if not rings:
            continue
        # Convert ArcGIS rings to GeoJSON-style coords (just keep the outer ring)
        out.append({
            "cluster_num": cnum,
            "cluster_name": f["attributes"].get("NBH_NAMES", ""),
            "rings": rings,
        })
    return out

# Categories we report on. Anything not in this list is grouped under "other".
USE_CATEGORIES = [
    "single_family", "condo", "multifamily",
    "office", "retail", "hotel_lodging", "industrial",
    "commercial_other", "institutional", "vacant", "other",
]

PRETTY_CAT = {
    "single_family": "Single-family",
    "condo": "Condo",
    "multifamily": "Multifamily",
    "office": "Office",
    "retail": "Retail",
    "hotel_lodging": "Hotel / lodging",
    "industrial": "Industrial",
    "commercial_other": "Commercial (other)",
    "institutional": "Institutional",
    "vacant": "Vacant land",
    "other": "Other",
}

RESIDENTIAL = {"single_family", "condo", "multifamily"}
COMMERCIAL = {"office", "retail", "hotel_lodging", "industrial", "commercial_other"}


def month_key(date_str):
    return date_str[:7] if date_str else ""


def safe_median(xs):
    return statistics.median(xs) if xs else 0


def main():
    src = os.path.join(DATA_DIR, "sales.json")
    print(f"Reading {src}…")
    with open(src) as fh:
        sales = json.load(fh)
    print(f"  {len(sales):,} sales loaded")

    # Filter out the small junk: $0 (shouldn't be there, sanity), missing dates,
    # and anything before 2020.
    sales = [
        s for s in sales
        if s.get("sale_date") and s.get("sale_price") and s["sale_price"] > 0
        and s["sale_date"] >= "2020-01-01"
    ]
    print(f"  {len(sales):,} after cleaning")

    # Drop the most recent month if it's not yet complete. DC's CAMA feed
    # is daily-ish, so the latest month often only has data through
    # whatever day we pulled on. Heuristic: if the latest date in the file
    # is earlier than day 28 of its month, that month is incomplete.
    if sales:
        last_date = max(s["sale_date"] for s in sales)
        last_day = int(last_date[8:10])
        if last_day < 28:
            cutoff_month = last_date[:7]
            sales = [s for s in sales if s["sale_date"][:7] < cutoff_month]
            print(f"  Dropped incomplete month {cutoff_month} ({last_date} was day {last_day})")
            print(f"  {len(sales):,} after dropping partial month")

    # -------- monthly time series ---------
    # Per (month, category): count + median price
    bucket = defaultdict(lambda: defaultdict(list))
    for s in sales:
        m = month_key(s["sale_date"])
        cat = s.get("use_category") or "other"
        bucket[m][cat].append(s["sale_price"])

    months_sorted = sorted(bucket.keys())
    monthly = []
    for m in months_sorted:
        row = {"month": m}
        for cat in USE_CATEGORIES:
            prices = bucket[m].get(cat, [])
            row[f"{cat}_count"] = len(prices)
            row[f"{cat}_median"] = int(safe_median(prices)) if prices else None
        # convenience aggregates
        res_prices = [p for cat in RESIDENTIAL for p in bucket[m].get(cat, [])]
        com_prices = [p for cat in COMMERCIAL for p in bucket[m].get(cat, [])]
        row["residential_count"] = len(res_prices)
        row["residential_median"] = int(safe_median(res_prices)) if res_prices else None
        row["commercial_count"] = len(com_prices)
        row["commercial_median"] = int(safe_median(com_prices)) if com_prices else None
        monthly.append(row)

    # Add 12-month trailing average for the noisy commercial series.
    def trailing_avg(arr, idx, key, window=12):
        start = max(0, idx - window + 1)
        vals = [arr[i][key] for i in range(start, idx + 1) if arr[i][key] is not None]
        if not vals:
            return None
        return int(sum(vals) / len(vals))

    for i, _ in enumerate(monthly):
        monthly[i]["residential_count_avg12"] = trailing_avg(monthly, i, "residential_count")
        monthly[i]["commercial_count_avg12"] = trailing_avg(monthly, i, "commercial_count")
        monthly[i]["residential_median_avg12"] = trailing_avg(monthly, i, "residential_median")
        monthly[i]["commercial_median_avg12"] = trailing_avg(monthly, i, "commercial_median")

    print(f"  monthly buckets: {len(monthly)} months from {monthly[0]['month']} to {monthly[-1]['month']}")

    # Annual roll-ups — cleaner storytelling than monthly noise.
    yearly = defaultdict(lambda: {"res": [], "com": []})
    for s in sales:
        y = s["sale_date"][:4]
        if s["use_category"] in RESIDENTIAL:
            yearly[y]["res"].append(s["sale_price"])
        elif s["use_category"] in COMMERCIAL:
            yearly[y]["com"].append(s["sale_price"])
    annual = []
    for y in sorted(yearly):
        annual.append({
            "year": y,
            "residential_count": len(yearly[y]["res"]),
            "residential_median": int(safe_median(yearly[y]["res"])) if yearly[y]["res"] else None,
            "commercial_count": len(yearly[y]["com"]),
            "commercial_median": int(safe_median(yearly[y]["com"])) if yearly[y]["com"] else None,
        })
    print(f"  annual buckets: {len(annual)} years")

    # -------- by-use totals + year-over-year ---------
    def collect(predicate):
        return [s for s in sales if predicate(s)]

    # Annualize 2026 YTD using prior-year seasonal weights, not a flat 12/N
    # ratio. Jan-Apr is typically below 1/3 of a year, so flat scaling under-
    # estimates the annual total. Compute the historical share of each
    # calendar month using 2021-2025 data (skipping 2020 because of COVID).
    months_observed_2026 = sorted({m for m in bucket if m.startswith("2026")})
    months_observed_indices = [int(m.split("-")[1]) for m in months_observed_2026]
    print(f"  2026 coverage: {len(months_observed_2026)} complete months "
          f"({months_observed_2026})")

    def seasonal_share(series_filter):
        """Average share of full-year sales that falls in the observed months,
        using each completed prior year as one sample."""
        shares = []
        for y in ["2021", "2022", "2023", "2024", "2025"]:
            yr_total, yr_observed_period = 0, 0
            for m, bucket_for_m in bucket.items():
                if not m.startswith(y):
                    continue
                count = sum(
                    len(bucket_for_m.get(cat, []))
                    for cat in (RESIDENTIAL if series_filter == "res"
                                else COMMERCIAL if series_filter == "com"
                                else USE_CATEGORIES)
                )
                yr_total += count
                if int(m.split("-")[1]) in months_observed_indices:
                    yr_observed_period += count
            if yr_total:
                shares.append(yr_observed_period / yr_total)
        return sum(shares) / len(shares) if shares else None

    seasonal_all = seasonal_share("all")
    seasonal_res = seasonal_share("res")
    seasonal_com = seasonal_share("com")
    print(f"  Historical Jan-Apr share — all: {seasonal_all:.3f}, res: {seasonal_res:.3f}, com: {seasonal_com:.3f}")

    def annualize(ytd, kind):
        share = {"all": seasonal_all, "res": seasonal_res, "com": seasonal_com}.get(kind)
        if not share or not ytd:
            return 0
        return int(round(ytd / share))

    by_use = []
    for cat in USE_CATEGORIES:
        cat_sales = collect(lambda s, c=cat: s.get("use_category") == c)
        prices = [s["sale_price"] for s in cat_sales]
        counts_by_year = {}
        medians_by_year = {}
        for y in ["2020", "2021", "2022", "2023", "2024", "2025", "2026"]:
            yr_sales = [s for s in cat_sales if s["sale_date"].startswith(y)]
            counts_by_year[y] = len(yr_sales)
            medians_by_year[y] = int(safe_median([s["sale_price"] for s in yr_sales])) if yr_sales else 0
        kind = "res" if cat in RESIDENTIAL else "com" if cat in COMMERCIAL else "all"
        annualized_2026 = annualize(counts_by_year["2026"], kind)
        by_use.append({
            "category": cat,
            "label": PRETTY_CAT[cat],
            "total_count": len(cat_sales),
            "median_price": int(safe_median(prices)) if prices else 0,
            "counts_by_year": counts_by_year,
            "medians_by_year": medians_by_year,
            "count_2026_annualized": annualized_2026,
            # back-compat with the old viewer
            "median_2024": medians_by_year["2024"],
            "median_2025": medians_by_year["2025"],
            "median_2026_ytd": medians_by_year["2026"],
            "count_2024": counts_by_year["2024"],
            "count_2025": counts_by_year["2025"],
            "count_2026_ytd": counts_by_year["2026"],
        })
    print(f"  by_use: {len(by_use)} categories")

    # -------- by neighborhood cluster ---------
    by_cluster_raw = defaultdict(list)
    for s in sales:
        if s.get("cluster_name") and s.get("cluster_num") is not None:
            by_cluster_raw[(s["cluster_num"], s["cluster_name"])].append(s)
    by_cluster = []
    for (cnum, cname), cs in by_cluster_raw.items():
        prices = [s["sale_price"] for s in cs]
        c_recent = [s for s in cs if s["sale_date"] >= "2025-01-01"]
        c_recent_res = [s for s in c_recent if s["use_category"] in RESIDENTIAL]
        c_recent_com = [s for s in c_recent if s["use_category"] in COMMERCIAL]

        # Per-year breakdowns (all / residential / commercial) for the map layers.
        counts_by_year = {}
        for y in ["2020", "2021", "2022", "2023", "2024", "2025", "2026"]:
            yr_sales = [s for s in cs if s["sale_date"].startswith(y)]
            yr_res = [s for s in yr_sales if s["use_category"] in RESIDENTIAL]
            yr_com = [s for s in yr_sales if s["use_category"] in COMMERCIAL]
            counts_by_year[y] = {
                "all": len(yr_sales),
                "residential": len(yr_res),
                "commercial": len(yr_com),
            }
        # Annualize 2026 with seasonal weighting per series
        counts_by_year["2026"]["all"] = annualize(counts_by_year["2026"]["all"], "all")
        counts_by_year["2026"]["residential"] = annualize(counts_by_year["2026"]["residential"], "res")
        counts_by_year["2026"]["commercial"] = annualize(counts_by_year["2026"]["commercial"], "com")

        by_cluster.append({
            "cluster_num": cnum,
            "cluster_name": cname,
            "total_count": len(cs),
            "median_price": int(safe_median(prices)) if prices else 0,
            "count_2024": counts_by_year["2024"]["all"],
            "count_2025": counts_by_year["2025"]["all"],
            "count_2026_ytd": counts_by_year["2026"]["all"],
            "count_recent": len(c_recent),
            "count_recent_residential": len(c_recent_res),
            "count_recent_commercial": len(c_recent_com),
            "median_recent": int(safe_median([s["sale_price"] for s in c_recent])) if c_recent else 0,
            "counts_by_year": counts_by_year,
        })
    by_cluster.sort(key=lambda r: r["total_count"], reverse=True)
    print(f"  by_cluster: {len(by_cluster)} clusters")

    # Cluster polygons — needed for the map.
    print(f"  Fetching cluster polygons for map…")
    polys = fetch_cluster_polygons()
    by_cluster_lookup = {c["cluster_num"]: c for c in by_cluster}
    clusters_geo = []
    for p in polys:
        stats = by_cluster_lookup.get(p["cluster_num"], {})
        clusters_geo.append({
            "cluster_num": p["cluster_num"],
            "cluster_name": p["cluster_name"],
            "rings": p["rings"],
            "count_recent": stats.get("count_recent", 0),
            "count_recent_residential": stats.get("count_recent_residential", 0),
            "count_recent_commercial": stats.get("count_recent_commercial", 0),
            "median_recent": stats.get("median_recent", 0),
            "counts_by_year": stats.get("counts_by_year", {}),
        })
    print(f"  cluster geometries: {len(clusters_geo)}")

    # -------- top sales 2025-2026 ---------
    recent = [s for s in sales if s["sale_date"] >= "2025-01-01"]
    recent.sort(key=lambda s: s["sale_price"], reverse=True)
    top = []
    for s in recent[:100]:
        top.append({
            "sale_date": s["sale_date"],
            "sale_price": s["sale_price"],
            "address": s["address"],
            "use_category": s["use_category"],
            "use_description": s["use_description"],
            "cluster_name": s.get("cluster_name", ""),
            "buyer": s["buyer"],
            "building_sqft": s.get("building_sqft"),
            "lat": s.get("lat"),
            "lon": s.get("lon"),
        })

    # -------- summary headline numbers ---------
    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "first_sale": sales[-1]["sale_date"] if sales else "",
        "last_sale": sales[0]["sale_date"] if sales else "",
        "total_sales": len(sales),
        "count_2020": sum(1 for s in sales if "2020-01-01" <= s["sale_date"] < "2021-01-01"),
        "count_2021": sum(1 for s in sales if "2021-01-01" <= s["sale_date"] < "2022-01-01"),
        "count_2022": sum(1 for s in sales if "2022-01-01" <= s["sale_date"] < "2023-01-01"),
        "count_2023": sum(1 for s in sales if "2023-01-01" <= s["sale_date"] < "2024-01-01"),
        "count_2024": sum(1 for s in sales if "2024-01-01" <= s["sale_date"] < "2025-01-01"),
        "count_2025": sum(1 for s in sales if "2025-01-01" <= s["sale_date"] < "2026-01-01"),
        "count_2026_ytd": sum(1 for s in sales if s["sale_date"] >= "2026-01-01"),
    }

    # -------- write all ---------
    def write(name, obj):
        out = os.path.join(DATA_DIR, name)
        with open(out, "w") as fh:
            json.dump(obj, fh, separators=(",", ":"))
        sz = os.path.getsize(out)
        print(f"  Wrote {name}  ({sz:,} bytes)")

    write("monthly.json", monthly)
    write("annual.json", annual)
    write("by_use.json", by_use)
    write("by_cluster.json", by_cluster)
    write("clusters_geo.json", clusters_geo)
    write("top_sales.json", top)
    write("summary.json", summary)


if __name__ == "__main__":
    main()
