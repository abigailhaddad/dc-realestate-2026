# Pipeline

Python data fetch + aggregation. Stdlib only — no `pip install`.

## Scripts (run in this order)

| Script | What it does | Outputs |
|---|---|---|
| `pull.py` | Pulls every qualified arms-length sale since 2020-01-01, plus parcel metadata + cluster polygons | `data/sales.json` |
| `pull_citywide.py` | Pulls all 30,867 tax-lot polygons + 221k ITSPE rows + CAMA year-built data, computes use-mix, owner aggregates, foreign-government parcels, and tax-exempt-by-cluster | `data/citywide_*.json` |
| `analyze.py` | Reads `data/sales.json`, buckets to monthly + yearly + by-use + by-cluster aggregates | `data/monthly.json`, `data/annual.json`, `data/by_use.json`, `data/by_cluster.json`, `data/clusters_geo.json`, `data/top_sales.json`, `data/summary.json` |

After running, copy the outputs the React app needs:

```bash
cp data/*.json ../public/
```

## Runtime cost

- `pull.py`: ~2 min (single-threaded HTTP against DC ArcGIS)
- `pull_citywide.py`: ~2 min
- `analyze.py`: ~5 sec (pure local computation)

Total ~5 min per full refresh. DC's APIs are uncached and unmetered.

## Common edits

### Add a new field to per-sale records

In `pull.py`, find the `itspe_fields` or `cama_fields` list, add the field
name. Then surface it in the row dict at the bottom of `main()`.

### Add a new field to citywide aggregates

In `pull_citywide.py`, find where you want it — most aggregates happen in a
single pass over the `itspe` list. Add a new accumulator in `use_mix_totals` /
`by_cluster_raw` / etc., and add it to the output dict.

### Time-bucket the data differently

`analyze.py` operates entirely on `data/sales.json` — change the bucket logic
in `main()`. The `monthly` list aggregates by `month_key()`; the `annual` list
by year prefix. Both write to separate output files.

## Gotchas

- **ArcGIS pagination**: default page size is 2,000 records. `arcgis_query()`
  pages automatically; don't add your own loop unless you also handle
  `resultOffset` and `exceededTransferLimit`.

- **POST fallback**: when a query payload (especially polygon `geometry`)
  exceeds ~7,000 chars URL-encoded, `http_get()` switches to POST. Don't
  bypass this helper.

- **Sentinel `1900-01-01` dates**: DC marks "we have no real transfer info" as
  `1900-01-01` in sales records. `analyze.py` strips these. If you build
  another time-series, do the same.

- **`USECODE` is a zero-padded string**: `"081"` not `81`. Always quote.

- **ITSPE has more rows than tax lots**: 221k vs 30k. Condos get one row per
  unit but share a tax lot. When counting "parcels", filter ITSPE.SSL through
  the Tax Lots layer (see `pull_citywide.py`).

## Caches

- `.osm_cache.json` — OpenStreetMap Nominatim results, used by `pull.py` for
  fallback parcel naming. Safe to delete; it'll re-populate on next run.

## Layer reference

See [`../docs/data_sources.md`](../docs/data_sources.md) for the full ArcGIS
endpoint catalog used by these scripts.
