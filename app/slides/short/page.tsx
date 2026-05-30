// A 5-minute version of the deck. The full version lives at /slides.
// Pick the 6 highest-impact slides; everything else is in the long deck.
import { promises as fs } from "fs";
import path from "path";
import { Deck, Slide, SlideTitle, SlideBody } from "@/components/Deck";
import { DataNote } from "@/components/DataNote";
import { YearBuiltMap } from "@/components/YearBuiltMap";
import { ForeignFlagMap } from "@/components/ForeignFlagMap";
import { SingleVolumeChart } from "@/components/SingleVolumeChart";
import type { Summary, MonthlyRow } from "@/lib/types";

type ParcelShapes = {
  categories: string[];
  parcels: [number, number | null, number, number, number][];
};
type ForeignParcel = {
  owner: string; lat: number; lon: number; assessed: number; address: string;
};

async function loadJson<T>(name: string): Promise<T> {
  const p = path.join(process.cwd(), "public", name);
  return JSON.parse(await fs.readFile(p, "utf-8")) as T;
}
async function tryLoad<T>(name: string, fallback: T): Promise<T> {
  try {
    return await loadJson<T>(name);
  } catch {
    return fallback;
  }
}

export default async function ShortSlidesPage() {
  const [summary, monthly, parcelShapes, foreignParcels] = await Promise.all([
    loadJson<Summary>("summary.json"),
    loadJson<MonthlyRow[]>("monthly.json"),
    tryLoad<ParcelShapes>("citywide_parcel_shapes.json", { categories: [], parcels: [] }),
    tryLoad<ForeignParcel[]>("citywide_foreign_parcels.json", []),
  ]);

  const slides = [
    // 1 — Title
    <Slide key="title">
      <h1 className="text-5xl font-semibold tracking-tight md:text-7xl leading-[1.05]">
        DC by the Parcel
      </h1>
      <p className="mt-4 text-xl md:text-2xl text-muted-foreground max-w-2xl">
        Building With DC Property Data
      </p>
      <div className="mt-10 grid gap-4 grid-cols-3 max-w-2xl">
        <TitleStat value="30,867" label="parcels" />
        <TitleStat value="221,163" label="properties" />
        <TitleStat value="419,425" label="sales" />
      </div>
      <div className="mt-12 flex items-baseline gap-3 text-base">
        <span className="font-medium text-foreground">Abigail Haddad</span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">DC Abundance Meetup</span>
      </div>
    </Slide>,

    // 2 — What's available
    <Slide key="layers">
      <SlideTitle eyebrow="What's in there">
        DC publishes <span className="text-foreground">every parcel</span>, free.
      </SlideTitle>
      <SlideBody>
        <p className="max-w-3xl">
          One ArcGIS REST endpoint per layer.
          {" "}<code className="text-foreground bg-muted px-1.5 py-0.5 rounded text-sm">maps2.dcgis.dc.gov</code>{" "}
          — no key, no rate limit, JSON over HTTP.
        </p>
        <div className="mt-6 grid grid-cols-1 gap-y-3 gap-x-8 sm:grid-cols-2 max-w-4xl text-base">
          <Source name="Tax Lots" desc="30,867 parcel polygons" />
          <Source name="Integrated Tax System Public Extract" desc="Owner, use code, assessed value, last sale" />
          <Source name="Property Sales" desc="Every recorded transaction" />
          <Source name="Computer Assisted Mass Appraisal" desc="Building sqft, year built" />
          <Source name="USECODE" desc="Religious, educational, residential, etc." />
          <Source name="Neighborhood Clusters" desc="46 labeled polygons" />
        </div>
      </SlideBody>
    </Slide>,

    // 3 — Year built map (visceral)
    <Slide key="year-built">
      <SlideTitle eyebrow="One thing this shows you">When DC was built.</SlideTitle>
      <div className="mt-4">
        {parcelShapes.parcels.length > 0 ? <YearBuiltMap data={parcelShapes} /> : null}
      </div>
    </Slide>,
    <DataNote
      key="year-built-data"
      vizTitle="When DC was built"
      layers={[
        { name: "Tax Lots", path: "Property_and_Land/FeatureServer/39", fields: ["SSL", "geometry → centroid"] },
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "Property_and_Land/FeatureServer/53", fields: ["SSL", "USECODE", "LANDAREA"] },
        { name: "Residential Computer Assisted Mass Appraisal", path: "Property_and_Land/FeatureServer/25", fields: ["SSL", "AYB"] },
        { name: "Commercial Computer Assisted Mass Appraisal", path: "Property_and_Land/FeatureServer/23", fields: ["SSL", "AYB"] },
      ]}
      notes="Each parcel gets its building's AYB (Actual Year Built) from one of the two Computer Assisted Mass Appraisal tables, keyed by SSL. Vacant parcels with no building come through as 'unknown'."
    />,

    // 4 — Foreign flag map (delightful)
    <Slide key="foreign">
      <SlideTitle eyebrow="Another thing this shows you">
        Foreign government land, by country.
      </SlideTitle>
      <div className="mt-4">
        {foreignParcels.length > 0 ? <ForeignFlagMap parcels={foreignParcels} /> : null}
      </div>
    </Slide>,
    <DataNote
      key="foreign-data"
      vizTitle="Foreign government land"
      layers={[
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "Property_and_Land/FeatureServer/53", fields: ["SSL", "OWNERNAME", "NEWTOTAL", "PREMISEADD"] },
        { name: "Tax Lots", path: "Property_and_Land/FeatureServer/39", fields: ["SSL", "geometry → centroid"] },
      ]}
      notes="Regex over OWNERNAME catches 'Government of X', 'Royal Y', 'Embassy of Z', etc. Then group by country, average centroid → flag location, sum NEWTOTAL → flag size."
    />,

    // 5 — The project (sales trend)
    <Slide key="sales">
      <SlideTitle eyebrow="One project I built">
        DC sales since 2020.
      </SlideTitle>
      <SlideBody>
        <p className="max-w-4xl text-2xl md:text-3xl mb-6 leading-snug">
          <span className="font-semibold">{summary.count_2021.toLocaleString()}</span> qualified sales in 2021 ·
          {" "}<span className="font-semibold">{summary.count_2025.toLocaleString()}</span> in 2025 ·
          {" "}<span className="font-semibold text-foreground">down 46% from the peak.</span>
        </p>
        <SingleVolumeChart
          monthly={monthly}
          series="residential"
          title="Residential sales by month"
          description="Thin line: raw monthly · thick line: 12-month trailing average"
          color="var(--chart-1)"
        />
      </SlideBody>
    </Slide>,
    <DataNote
      key="sales-data"
      vizTitle="DC residential sales since 2020"
      layers={[
        { name: "Property Sales (Computer Assisted Mass Appraisal)", path: "Property_and_Land/FeatureServer/57", fields: ["SSL", "SALE_DATE", "SALE_PRICE", "QUALIFIED"] },
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "Property_and_Land/FeatureServer/53", fields: ["SSL", "USECODE → category"] },
      ]}
      notes="Filter to QUALIFIED = 'Q' (arms-length) and SALE_PRICE > 0, since 2020-01-01. Use codes 011-029 = residential. Bucket by month, compute 12-month rolling average."
    />,

    // 6 — Things you could make
    <Slide key="ideas">
      <SlideTitle eyebrow="Take this further">Things you could make.</SlideTitle>
      <SlideBody>
        <div className="grid gap-3 sm:grid-cols-2 max-w-4xl mt-2">
          <Idea title="Surface parking lot map"
            desc={<><b>Surface parking</b> in DC. Headline acres within walking of the Capitol.</>} />
          <Idea title="Church-to-condo tracker"
            desc={<>Religious parcels that <b>flipped to residential</b>.</>} />
          <Idea title="Vacant &amp; blighted dashboard"
            desc={<>DC's official <b>vacant/blighted</b> registry, mapped.</>} />
          <Idea title="Sales near Metro"
            desc={<>Cross-join with <b>WMATA</b> station locations.</>} />
        </div>
      </SlideBody>
    </Slide>,

    // Stack credit
    <Slide key="built-with">
      <SlideTitle eyebrow="The stack">Built with.</SlideTitle>
      <SlideBody>
        <div className="grid gap-4 sm:grid-cols-2 max-w-4xl mt-2">
          <StackItem name="Claude Code" desc="Anthropic's CLI agent. The actual dev partner. Wrote most of this code." />
          <StackItem name="Python (stdlib only)" desc="No requests, no pandas. urllib + json + datetime for the pipeline." />
          <StackItem name="Next.js + Tailwind CSS" desc="App Router, server-rendered pages. Tailwind v4 for styling." />
          <StackItem name="shadcn/ui" desc="Radix-based components for cards, tabs, badges. Brand colors via CSS variables." />
          <StackItem name="Recharts" desc="Line + bar charts. Inherits theme tokens automatically." />
          <StackItem name="Leaflet + OpenStreetMap" desc="Map base + tiles. No API key, no rate limits." />
        </div>
      </SlideBody>
    </Slide>,

    // Final — Close
    <Slide key="close">
      <SlideTitle eyebrow="If you want to try it">Where to start.</SlideTitle>
      <SlideBody>
        <div className="space-y-4 max-w-3xl">
          <Item title="DC's catalog">
            <code className="text-foreground bg-muted px-1.5 py-0.5 rounded text-sm">
              opendata.dc.gov/api/feed/dcat-us/1.1.json
            </code>
          </Item>
          <Item title="The base server">
            <code className="text-foreground bg-muted px-1.5 py-0.5 rounded text-sm">
              maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA
            </code>
          </Item>
          <Item title="This repo">
            <code className="text-foreground bg-muted px-1.5 py-0.5 rounded text-sm">
              dc-realestate-2026
            </code> · ~600 LOC · zero ext deps
          </Item>
        </div>
      </SlideBody>
    </Slide>,
  ];

  return <Deck slides={slides} />;
}

function TitleStat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="text-3xl font-semibold tabular-nums">{value}</div>
      <div className="text-sm text-muted-foreground uppercase tracking-wide">{label}</div>
    </div>
  );
}
function Source({ name, desc }: { name: string; desc: string }) {
  return (
    <div>
      <div className="font-medium">{name}</div>
      <div className="text-sm text-muted-foreground">{desc}</div>
    </div>
  );
}
function Idea({ title, desc }: { title: string; desc: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="font-medium text-base">{title}</div>
      <div className="mt-1.5 text-sm text-muted-foreground">{desc}</div>
    </div>
  );
}
function Item({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1">{title}</div>
      <div className="text-base">{children}</div>
    </div>
  );
}

function StackItem({ name, desc }: { name: string; desc: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="font-semibold text-lg" style={{ color: "#2D6A4F" }}>{name}</div>
      <div className="mt-1 text-sm text-muted-foreground">{desc}</div>
    </div>
  );
}
