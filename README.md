# DC Real Estate 2026

An end-to-end example of pulling DC's open property data from its public ArcGIS
REST APIs and turning it into an interactive dashboard + briefing decks.

The core of this repo is the **data pipeline**: dependency-free Python scripts
that hit DC's property APIs — sales, parcels, ownership, assessments — and
handle the awkward parts (pagination, POST fallback for big polygon queries,
the tax-lot vs. ITSPE distinction) so you get clean JSON out. The dashboard and
decks are just one thing you can do with that data.

If you came here for the APIs, start with
[`docs/data_sources.md`](./docs/data_sources.md) (every layer + the fields it
exposes) and [`pipeline/README.md`](./pipeline/README.md) (how the scripts
work and how to extend them).

## What you get

> ### 🎤 The lightning-talk deck → [`/slides/short`](http://localhost:3000/slides/short)
> An 11-slide version built for a 5-minute talk (presented at the DC Abundance
> Meetup). Keyboard nav, live charts, fullscreen **Present** button. Start here.

| Route | What it is |
|---|---|
| `/slides/short` | **🎤 Lightning-talk deck** — 11 slides, ~5 min. The headline version. |
| `/slides` | Full briefing deck — 30 slides, same charts in more depth. |
| `/` | Interactive dashboard — summary cards, monthly trend chart for residential + commercial sales, neighborhood-cluster sales map (animated), top sales table, by-use heatmap. |

All three have keyboard nav (← / →), an `F` fullscreen toggle, and a **Present** button.

## Quick start

```bash
# 1. Install JS deps
pnpm install

# 2. Pull the data (~3 minutes — see pipeline/README.md)
cd pipeline
python3 pull.py            # qualified sales since 2020, with metadata
python3 pull_citywide.py   # citywide ITSPE + parcel geometries
python3 analyze.py         # roll up into report-friendly JSON
cd ..

# 3. Copy the aggregates the React app reads
cp data/*.json public/

# 4. Run the site
pnpm dev
```

Open <http://localhost:3000/slides/short> for the lightning-talk deck. The full
deck is at `/slides`; the dashboard at `/`.

For any deck: arrow keys to navigate, `F` to toggle fullscreen, the **Present**
button does the same.

## Export the decks to static HTML

The whole site is static (`output: "export"` in `next.config.ts`), so you can
ship the decks as plain HTML files — no server needed at runtime:

```bash
pnpm build          # writes the site to out/
```

This produces:

- `out/slides/short.html` — the lightning-talk deck
- `out/slides.html` — the full deck
- `out/index.html` — the dashboard

To preview the static build locally (the HTML references absolute `/_next/…`
asset paths, so open it through a server, not `file://`):

```bash
cd out && python3 -m http.server 8099
# then open http://localhost:8099/slides/short.html
```

## What's in the repo

```
dc-realestate-2026/
├── pipeline/              Python data scripts (stdlib only, no deps)
│   ├── pull.py              Sale-by-sale data + per-parcel metadata
│   ├── pull_citywide.py     ALL DC parcels — geometry, owner, year built, use
│   ├── analyze.py           Aggregates sale data to monthly/yearly buckets
│   └── README.md
├── data/                  Generated JSON (.gitignored except aggregates)
├── public/                JSON consumed by the React app at runtime
├── app/                   Next.js App Router pages
│   ├── page.tsx             Dashboard
│   └── slides/page.tsx      Briefing deck
├── components/            React UI (cards, charts, maps, deck)
├── lib/                   Shared types + utilities
├── docs/
│   └── data_sources.md    Full reference for every ArcGIS endpoint used
├── README.md              You are here
├── CLAUDE.md              Instructions for Claude in this codebase
└── package.json
```

## Data sources

All data is from the DC Office of Tax & Revenue + adjacent agencies, served
via Esri ArcGIS REST on `maps2.dcgis.dc.gov`. No API keys, no rate limits, no
sign-up. See [`docs/data_sources.md`](./docs/data_sources.md) for the full layer
catalog and join patterns.

To find layers beyond the ones used here, browse the full DC open-data catalog
at `https://opendata.dc.gov/api/feed/dcat-us/1.1.json`. To pull a new one, point
the HTTP helpers in [`pipeline/pull.py`](./pipeline/pull.py) (`http_get`,
`arcgis_query`, `in_chunks`) at its endpoint — they handle pagination and the
URL-too-long → POST fallback for you.

The single external dependency — only as a fallback — is
[OpenStreetMap Nominatim](https://nominatim.openstreetmap.org/) for naming
parcels that DC's datasets list anonymously (e.g. "DC government property" →
"Blair Shelter"). Free, 1 request per second, no key. Cached to disk.

## Stack

- **Pipeline**: Python 3.10+ (stdlib only)
- **Site**: Next.js 16 (App Router) + Tailwind CSS + shadcn/ui + Recharts + Leaflet
- **No backend** — everything is static after pipeline + `pnpm build`

## License

Data: DC OTR open data, public domain.
Code: MIT (see [`LICENSE`](./LICENSE)).
