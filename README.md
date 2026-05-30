# DC Real Estate 2026

A polished, end-to-end example of pulling DC's open property data and turning
it into an interactive dashboard + briefing deck.

Built as a reference for anyone — including Claude — who wants to **start a new
project on top of DC's public APIs** without spending two days figuring out
which layers to hit.

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

## How to use this as a starter for a new project

You're handing this to Claude and saying "make me something like this for X." A
few entry points:

1. **Change the question, keep the pipeline.** The pulls in `pipeline/` are
   general — they fetch every parcel and every sale. Edit `analyze.py` (or add
   a new analyze script) to compute whatever aggregate you want.

2. **Add a new visualization.** Charts are isolated React components in
   `components/`. Copy the pattern of `UseMixChart.tsx` (Recharts) or
   `SalesMapImpl.tsx` (Leaflet). Map components need a thin dynamic-import
   wrapper (e.g. `SalesMap.tsx` → `SalesMapImpl.tsx`) because Leaflet touches
   `window` at import time.

3. **Add a new slide.** Open `app/slides/page.tsx`, add a `<Slide>` to the
   `slides` array. Each slide is just a React node.

4. **Pull a different layer.** Browse `docs/data_sources.md` for what's available.
   The full DC catalog is at `https://opendata.dc.gov/api/feed/dcat-us/1.1.json`
   — search it for the topic you want. The HTTP helpers in `pipeline/pull.py`
   (`http_get`, `arcgis_query`, `in_chunks`) handle pagination + URL-too-long
   automatically.

See [`CLAUDE.md`](./CLAUDE.md) for a more detailed brief aimed at Claude.

## Data sources

All data is from the DC Office of Tax & Revenue + adjacent agencies, served
via Esri ArcGIS REST on `maps2.dcgis.dc.gov`. No API keys, no rate limits, no
sign-up. See [`docs/data_sources.md`](./docs/data_sources.md) for the full layer
catalog and join patterns.

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
