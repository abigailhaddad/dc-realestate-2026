"""
Citywide DC parcel attributes for the pattern screens (patterns.py).

  ITSPE (layer 53): use code, neighborhood, address, assessments, and three
    fields about the CURRENT owner's holding that say nothing about who it is:
      HSTDCODE   homestead / senior deduction code (None = no deduction claimed)
      MORTGAGECO reduced here to a yes/no: is a tax-escrow servicer on file
                 (CoreLogic, Lereta, a bank). Yes implies a mortgage with escrow;
                 no means cash OR a loan without escrow, so it's weak evidence.
      ACCEPTCODE OTR's text label for the latest sale (Market Sale, Unusual, ...)
  Residential CAMA (25) GBA/BEDRM and condo CAMA (24) LIVING_GBA/BEDRM for size.

OWNERNAME, OWNNAME2, CAREOFNAME and the mailing address are never requested.
    python3 pull_parcels.py -> .cache/parcels.json
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from pull import http_get  # noqa: E402
B = "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Property_and_Land_WebMercator/MapServer"

def all_rows(layer, fields):
    out, last = [], 0
    while True:
        r = http_get(f"{B}/{layer}/query", {"where": f"OBJECTID > {last}", "orderByFields": "OBJECTID", "outFields": "OBJECTID," + fields,
                                           "returnGeometry": "false", "f": "json", "resultRecordCount": 2000})
        if "error" in r:
            raise RuntimeError(r["error"])
        f = [x["attributes"] for x in r.get("features", [])]
        if not f:
            return out
        last = f[-1]["OBJECTID"]; out += f
        print(layer, len(out), end="\r", flush=True)

def main():
    it = all_rows(53, "SSL,USECODE,NBHD,NBHDNAME,PREMISEADD,LANDAREA,OLDTOTAL,NEWTOTAL,CY1YEAR,HSTDCODE,MORTGAGECO,ACCEPTCODE,SALEDATE,SALEPRICE")
    for r in it:
        r["escrow_servicer"] = bool((r.pop("MORTGAGECO") or "").strip())
        if r.get("SALEDATE"):
            r["SALEDATE"] = datetime.fromtimestamp(r["SALEDATE"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    res = all_rows(25, "SSL,GBA,BEDRM,AYB,BLDG_NUM")
    condo = all_rows(24, "SSL,LIVING_GBA,BEDRM,AYB")
    json.dump({"pulled_at": datetime.now(timezone.utc).isoformat(), "itspe": it, "res": res, "condo": condo},
              open(os.path.join(HERE, ".cache", "parcels.json"), "w"))
    print(f"\nitspe {len(it)}  res {len(res)}  condo {len(condo)}")

if __name__ == "__main__":
    main()
