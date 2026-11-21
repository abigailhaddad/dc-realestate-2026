"""
DC sales history 2015+ for every property (OTR layer 57), for checks that need
more than the 2025+ window pull_flag_inputs.py takes: "buyer later resold at a
loss" and own-history comparisons.

Why (2026-11-21 review): the overpriced screen only catches one shape (high
price on a 2025+ house sale). An overpayment can also show up later, when the
buyer resells for much less. That needs the earlier purchase in hand.

Fields: SSL, SALE_DATE, SALE_PRICE, QUALIFIED, SALE_CODE. No names (the layer
has none).    python3 pull_history.py -> .cache/sales_2015.json
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pull import http_get  # noqa: E402
URL = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Property_and_Land_WebMercator/MapServer/57/query"
SINCE = "2015-01-01"

def main():
    out, last = [], 0
    # page by OBJECTID (offset paging on 160K rows is slow on this server)
    while True:
        r = http_get(URL, {"where": f"SALE_DATE >= DATE '{SINCE}' AND OBJECTID > {last}", "orderByFields": "OBJECTID",
                           "outFields": "OBJECTID,SSL,SALE_DATE,SALE_PRICE,QUALIFIED,SALE_CODE",
                           "returnGeometry": "false", "f": "json", "resultRecordCount": 2000})
        if "error" in r:
            raise RuntimeError(r["error"])
        f = [x["attributes"] for x in r.get("features", [])]
        if not f:
            break
        last = f[-1]["OBJECTID"]
        for a in f:
            if a.get("SALE_DATE") is not None:
                a["SALE_DATE"] = datetime.fromtimestamp(a["SALE_DATE"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                out.append(a)
        print(len(out), end="\r", flush=True)
    json.dump({"pulled_at": datetime.now(timezone.utc).isoformat(), "since": SINCE, "sales": out},
              open(os.path.join(HERE, ".cache", "sales_2015.json"), "w"))
    print(f"\n{len(out)} sales since {SINCE}")

if __name__ == "__main__":
    main()
