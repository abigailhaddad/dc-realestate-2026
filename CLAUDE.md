# Instructions for Claude in this codebase

This repo is meant to be a starter for new projects on top of DC's open
property data. When someone hands you this repo and asks for a new feature, a
new visualization, or a whole new project built on the same data, this file is
where you start.

## The mental model

This is a **two-stage pipeline** with a static frontend:

```
DC ArcGIS REST endpoints
        │
        ▼  (pipeline/pull*.py — Python stdlib, no deps)
    data/*.json  (raw + medium-sized intermediate files)
        │
        ▼  (cp into public/)
    public/*.json  (the React app reads these via fs.readFile at build time)
        │
        ▼  (Next.js App Router — server components do the file reads)
    Rendered HTML + interactive client components
```

Everything in `data/` is regenerable. Don't treat any JSON file as authoritative
— the source of truth is DC's APIs. If something looks wrong, re-run the
relevant `pipeline/` script.

## Conventions worth knowing before you edit

1. **No build step in the pipeline.** All Python is stdlib only — `urllib`,
   `json`, `re`, `datetime`. Don't add `requests` or `pandas`. The HTTP helper
   in `pipeline/pull.py` (`http_get` / `arcgis_query`) handles GET → POST
   fallback when polygon payloads make URLs too long, and pagination at the
   ArcGIS 2,000-row default page size.

2. **Leaflet maps need dynamic imports.** Leaflet touches `window` at import
   time, so any component that uses `react-leaflet` MUST be split into two
   files: `Foo.tsx` (a thin client wrapper using `next/dynamic` with
   `ssr: false`) and `FooImpl.tsx` (the actual leaflet-using component). See
   `components/SalesMap.tsx` / `components/SalesMapImpl.tsx` for the pattern.

3. **Use codes are strings.** ITSPE's `USECODE` is zero-padded — `"081"`, not
   `81`. Always quote when filtering.

4. **DC has TWO levels of property identifier:**
   - **Tax lots** (~30,000) — physical parcels with polygons. From layer `/39`.
   - **ITSPE / SSL** (~221,000) — one row per legal property, which includes a
     separate row for every condo unit.
   When the question is "how many of X are there?", be explicit about which one
   you mean. Pulls in this repo dedupe to tax lots by intersecting ITSPE.SSL
   with the Tax Lots layer.

5. **Naming convention for components:**
   - `XxxChart.tsx` / `XxxTable.tsx` — Recharts / shadcn, server-rendered OK
   - `XxxMap.tsx` — thin client wrapper (`"use client"` + `next/dynamic`)
   - `XxxMapImpl.tsx` — the actual Leaflet code (also `"use client"`)
   - `SectionDivider`, `Deck`, `Slide`, `SlideTitle`, `SlideBody` — deck primitives

## Common tasks

### "Add a slide showing X"

1. If X needs new data — add a function in the appropriate `pipeline/pull*.py`
   that emits a new JSON file under `data/`. Re-run it. `cp` to `public/`.
2. Add a TypeScript type for the JSON shape in `lib/types.ts`.
3. Build a React component in `components/` — copy the pattern of an existing
   one. Recharts for bars / lines / scatter; Leaflet for maps; plain HTML for
   tables.
4. Import + place in the `slides` array in `app/slides/page.tsx`.

### "Add a column to the dashboard table"

Open `components/TopSalesTable.tsx` (or whichever table). Add to the column
header AND the row template. If the column needs a new data field, surface it
from `pipeline/pull.py` (the per-sale fields) or `pipeline/analyze.py` (the
aggregates). Update the type in `lib/types.ts`.

### "Pull a new ArcGIS layer"

Find the layer URL in [`docs/data_sources.md`](./docs/data_sources.md) or the
DC DCAT catalog. Add it as a constant at the top of `pipeline/pull.py` or
`pipeline/pull_citywide.py`. Use `arcgis_query(url, where=..., outFields=...)`.

Things that bite:
- ArcGIS sometimes silently truncates at 2,000 results — `arcgis_query` handles
  this by paging on `resultOffset`.
- For spatial intersect queries, the polygon payload often exceeds the URL
  length limit. `http_get` falls back to POST when the encoded params get long.
- Date fields come back as Unix-ms ints — convert with `fmt_date`.

## Things to NOT do without asking

- Don't move JSON files between `data/` and `public/` manually if you're
  generating them; the convention is `data/` → cp → `public/`. `data/` is the
  staging area; `public/` is what the runtime serves.
- Don't commit `data/sales.json`, `data/citywide_parcels.json`, or
  `data/citywide_parcel_shapes.json` — they're 1–18MB, .gitignored, and
  trivially regenerable.
- Don't add a backend / API route. Everything is static; if you need
  computation, do it in Python ahead of time.
- Don't replace the stack. Stick with Next.js App Router + Tailwind + shadcn +
  Recharts + Leaflet unless explicitly asked.

## When in doubt

Read `pipeline/pull.py` first — it's the most carefully written file in the
repo and demonstrates the ArcGIS access patterns. Then `app/slides/page.tsx`
to see how slides compose. Then `components/SingleVolumeChart.tsx` for a
canonical Recharts component and `components/SalesMapImpl.tsx` for a canonical
Leaflet one.
