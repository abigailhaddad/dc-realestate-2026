# Data sources

All data is from the DC Office of Tax & Revenue's open data, served via ArcGIS REST.
No API key required.

## Base server

```
https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA
```

## Layers used by `pipeline/pull.py`

| Layer | Used for | Key fields |
|---|---|---|
| `Property_and_Land_WebMercator/FeatureServer/57` — Property Sales (CAMA) | Full sale history per parcel | `SSL`, `SALE_DATE`, `SALE_PRICE`, `QUALIFIED`, `SALE_CODE`, `SALE_CURR_OWNER` |
| `Property_and_Land_WebMercator/FeatureServer/53` — ITSPE | Per-parcel use code + address + owner | `SSL`, `USECODE`, `PREMISEADD`, `OWNERNAME`, `LANDAREA`, `NBHD`, `NEWTOTAL` |
| `Property_and_Land_WebMercator/FeatureServer/23` — Commercial CAMA | Building details | `SSL`, `LIVING_GBA`, `AYB`, `NUM_UNITS` |
| `Property_and_Land_WebMercator/FeatureServer/25` — Residential CAMA | Building details | `SSL`, `LIVING_GBA`, `AYB`, `BEDRM` |
| `Property_and_Land_WebMercator/FeatureServer/54` — USECODE | Code → description lookup | `CODE`, `DESCRIPTION` |
| `Property_and_Land_WebMercator/FeatureServer/39` — Tax Lots | Parcel polygons for centroid + cluster join | `SSL` + geometry |
| `Administrative_Other_Boundaries_WebMercator/MapServer/17` — Neighborhood Clusters | Labeled neighborhood polygons | `NAME`, `NBH_NAMES` + geometry |

## Filters applied

The pull script intentionally drops a lot of noise:

- **Qualified only** (`QUALIFIED = 'Q'`) — DC's flag for arms-length sales. Excludes $0 transfers, family transfers, trustee changes, multi-parcel deals where the price was assigned to a sibling lot.
- **Non-zero price** — defensive against bad rows.
- **From 2020-01-01 forward** — six-and-some years gives a useful baseline pre- and post-rate-hike cycle.

Result: ~45,000 sales records, ~50 MB of raw JSON aggregating down to ~90 KB of report-ready data.

## What this dataset cannot tell you

- **Rental / lease activity.** Most commercial activity is leases, not sales. CAMA only captures transactions.
- **Vacancy and occupancy** — separate data sources (DC Vacant/Blighted registry is partial).
- **Why volume changed.** Sales records show the transactions, not motivations. Rate cycles, WFH, federal labor shifts all blend into the same numbers.
- **Suburban metro context.** DC-only. MD/VA suburbs experience the same labor shifts but aren't in this data.

## Gotchas worth knowing

- `USECODE` is a zero-padded string (`'081'`, not `81`).
- `SALEDATE = '1900-01-01'` is DC's sentinel for "we know nothing about this transfer." Filtered out in `analyze.py`.
- Geometry queries with polygon payloads exceed URL length — `pull.py` switches to POST automatically.
- Pagination is per-layer at 2000 records; the helper functions loop until exhausted.
