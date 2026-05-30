import { promises as fs } from "fs";
import path from "path";
import { Deck, Slide, SlideTitle, SlideBody } from "@/components/Deck";
import { DataNote } from "@/components/DataNote";
import { SectionDivider } from "@/components/SectionDivider";
import { YearBuiltMap } from "@/components/YearBuiltMap";
import { TopOwners } from "@/components/TopOwners";
import { TaxExemptMap } from "@/components/TaxExemptMap";
import { UseMixChart } from "@/components/UseMixChart";
import { ParcelCategoryMap } from "@/components/ParcelCategoryMap";
import { ForeignFlagMap } from "@/components/ForeignFlagMap";
import { BiggestSalesMap } from "@/components/BiggestSalesMap";
import { SalesMap } from "@/components/SalesMap";
import { SingleVolumeChart } from "@/components/SingleVolumeChart";
import type { Summary, MonthlyRow, ClusterGeo, TopSale } from "@/lib/types";

type CitywideParcels = {
  categories: string[];
  parcels: [number, number, number | null, number][];
};
type ParcelShapes = {
  categories: string[];
  parcels: [number, number | null, number, number, number][];
};
type Owner = { owner: string; parcels: number; assessed_total: number };
type UseMixRow = {
  category: string;
  count: number;
  parcels?: number;
  share_count: number;
  land_sqft: number;
  share_land: number;
  assessed: number;
  share_assessed: number;
};
type CitywideCluster = {
  cluster_num: number;
  cluster_name: string;
  rings: number[][][];
  parcels: number;
  assessed_total: number;
  assessed_exempt: number;
  exempt_share: number;
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

export default async function SlidesPage() {
  const [summary, monthly, clustersGeo, parcels, parcelShapes, owners, foreignParcels, useMix, citywideClusters, topSales] =
    await Promise.all([
      loadJson<Summary>("summary.json"),
      loadJson<MonthlyRow[]>("monthly.json"),
      loadJson<ClusterGeo[]>("clusters_geo.json"),
      tryLoad<CitywideParcels>("citywide_parcels.json", { categories: [], parcels: [] }),
      tryLoad<ParcelShapes>("citywide_parcel_shapes.json", { categories: [], parcels: [] }),
      tryLoad<Owner[]>("citywide_owners.json", []),
      tryLoad<{owner:string;lat:number;lon:number;assessed:number;address:string}[]>("citywide_foreign_parcels.json", []),
      tryLoad<UseMixRow[]>("citywide_use_mix.json", []),
      tryLoad<CitywideCluster[]>("citywide_clusters.json", []),
      tryLoad<TopSale[]>("top_sales.json", []),
    ]);

  const slides = [
    // ── Title ────────────────────────────────────────────
    <Slide key="title">
      <h1 className="text-5xl font-semibold tracking-tight md:text-7xl leading-[1.05]">
        DC by the Parcel
      </h1>
      <p className="mt-4 text-xl md:text-2xl text-muted-foreground max-w-2xl">
        Building With DC Property Data
      </p>
      <div className="mt-8 grid gap-4 grid-cols-3 max-w-2xl">
        <TitleStat value="30,867" label="parcels" />
        <TitleStat value="221,163" label="properties" />
        <TitleStat value="419,425" label="sales" />
      </div>
      <div className="mt-16 flex items-baseline gap-3 text-base">
        <span className="font-medium text-foreground">Abigail Haddad</span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">DC Abundance Meetup</span>
      </div>
      <div className="mt-2 text-xs text-muted-foreground">
        Press → to advance · ← to go back
      </div>
    </Slide>,

    // ── Agenda ───────────────────────────────────────────
    <Slide key="agenda">
      <SlideTitle eyebrow="What we&apos;ll cover">Four things, in order.</SlideTitle>
      <div className="mt-8 space-y-8 max-w-3xl">
        <AgendaItem
          num="One."
          title="DC publishes parcel-level data on every property in the city."
          desc="Location, ownership, building details, and full sale history — public, free, no API key."
        />
        <AgendaItem
          num="Two."
          title="Here&apos;s what you can do with it."
          desc="Six examples that fall out of the data: building age, use mix, top owners, foreign government landholdings, tax-exempt land, biggest deals."
        />
        <AgendaItem
          num="Three."
          title="Here&apos;s a project I built with it."
          desc="A look at DC's residential and commercial sales since 2020 — what the data alone can show you about the market."
        />
        <AgendaItem
          num="Four."
          title="Other things you could build."
          desc="A short list of projects that fall out of the same data, in case anyone wants to pick one up."
        />
      </div>
    </Slide>,

    // ═══ PART ONE ════════════════════════════════════════
    <SectionDivider
      key="div-1"
      number="One"
      title="The data is available."
      subtitle="What's in DC's open property API and how the layers fit together."
    />,

    <Slide key="layers">
      <SlideTitle eyebrow="Six core layers">One join key.</SlideTitle>
      <SlideBody>
        <p className="max-w-3xl text-muted-foreground mb-6">
          Everything joins on <code className="text-foreground bg-muted px-1.5 py-0.5 rounded text-sm">SSL</code> (Square / Suffix / Lot).
          Each layer is an ArcGIS REST endpoint that returns JSON. Public, no authentication, no rate limit.
        </p>
        <div className="grid grid-cols-1 gap-y-4 gap-x-8 sm:grid-cols-2 max-w-4xl">
          <Source name="Tax Lots" desc="30,867 parcel polygons" />
          <Source name="Integrated Tax System Public Extract" desc="221,163 rows — owner, address, use code, assessed value, last sale" />
          <Source name="Property Sales (Computer Assisted Mass Appraisal)" desc="419,425 transactions back to digitization" />
          <Source name="Commercial &amp; Residential Computer Assisted Mass Appraisal" desc="Building square footage, year built, structure class" />
          <Source name="USECODE lookup" desc="081 = Religious, 083 = Educational, etc." />
          <Source name="Neighborhood Clusters" desc="46 labeled polygons (e.g. Cluster 26 = Capitol Hill, Lincoln Park)" />
        </div>
      </SlideBody>
    </Slide>,

    // ═══ PART TWO ════════════════════════════════════════
    <SectionDivider
      key="div-2"
      number="Two"
      title="Here are some examples."
      subtitle="A short menu of things that fall out of the data set."
    />,

    <Slide key="year-built">
      <SlideTitle eyebrow="Building age">When DC was built.</SlideTitle>
      <div className="mt-4">
        {parcelShapes.parcels.length > 0 ? <YearBuiltMap data={parcelShapes} /> : <Placeholder />}
      </div>
    </Slide>,
    <DataNote
      key="year-built-data"
      vizTitle="When DC was built"
      layers={[
        { name: "Tax Lots", path: "/FeatureServer/39", fields: ["SSL", "geometry → centroid"] },
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "/FeatureServer/53", fields: ["SSL", "USECODE", "LANDAREA"] },
        { name: "Residential Computer Assisted Mass Appraisal", path: "/FeatureServer/25", fields: ["SSL", "AYB"] },
        { name: "Commercial Computer Assisted Mass Appraisal", path: "/FeatureServer/23", fields: ["SSL", "AYB"] },
      ]}
      notes="Each parcel gets its building's AYB (Actual Year Built) from one of the two Computer Assisted Mass Appraisal tables, keyed by SSL. Parcels with no building → 'unknown'."
    />,

    <Slide key="use-mix">
      <SlideTitle eyebrow="Use mix">What DC is made of.</SlideTitle>
      <div className="mt-4">
        {useMix.length > 0 ? <UseMixChart rows={useMix} /> : <Placeholder />}
      </div>
    </Slide>,
    <DataNote
      key="use-mix-data"
      vizTitle="What DC is made of"
      layers={[
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "/FeatureServer/53", fields: ["SSL", "USECODE", "LANDAREA", "NEWTOTAL"] },
        { name: "USECODE lookup", path: "/FeatureServer/54", fields: ["CODE", "DESCRIPTION"] },
        { name: "Tax Lots", path: "/FeatureServer/39", fields: ["SSL (for dedup to physical parcels)"] },
      ]}
      notes="The Integrated Tax System Public Extract has 221k rows but DC has only ~30k tax lots — condos each get a row. Dedup the Square / Suffix / Lot identifier through the Tax Lots layer so each physical parcel is counted once."
    />,

    <Slide key="use-mix-map">
      <SlideTitle eyebrow="Use mix, mapped">Every parcel, by category.</SlideTitle>
      <div className="mt-4">
        {parcelShapes.parcels.length > 0 ? (
          <ParcelCategoryMap data={parcelShapes} />
        ) : (
          <Placeholder />
        )}
      </div>
    </Slide>,
    <DataNote
      key="use-mix-map-data"
      vizTitle="Every parcel, by category"
      layers={[
        { name: "Tax Lots", path: "/FeatureServer/39", fields: ["SSL", "geometry → centroid"] },
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "/FeatureServer/53", fields: ["SSL", "USECODE", "LANDAREA"] },
      ]}
      notes="USECODE categories binned to 5 buckets (Residential / Commercial / Institutional / Vacant / Other) so 30,000 dots remain legible at city zoom. Dot radius scales with LANDAREA."
    />,

    <Slide key="owners">
      <SlideTitle eyebrow="Top owners">Who owns DC&apos;s parcels.</SlideTitle>
      <div className="mt-4">
        {owners.length > 0 ? <TopOwners owners={owners} limit={20} /> : <Placeholder />}
      </div>
    </Slide>,
    <DataNote
      key="owners-data"
      vizTitle="Top DC owners"
      layers={[
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "/FeatureServer/53", fields: ["OWNERNAME", "NEWTOTAL"] },
      ]}
      notes="GroupBy OWNERNAME across all 221k Integrated Tax System Public Extract rows, sort by parcel count. UNITED STATES OF AMERICA and DISTRICT OF COLUMBIA dominate; private LLCs surface in the long tail."
    />,

    <Slide key="foreign">
      <SlideTitle eyebrow="Foreign government land">Embassies, on the map.</SlideTitle>
      <div className="mt-4">
        {foreignParcels.length > 0 ? <ForeignFlagMap parcels={foreignParcels} /> : <Placeholder />}
      </div>
    </Slide>,
    <DataNote
      key="foreign-data"
      vizTitle="Foreign government land"
      layers={[
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "/FeatureServer/53", fields: ["SSL", "OWNERNAME", "NEWTOTAL", "PREMISEADD"] },
        { name: "Tax Lots", path: "/FeatureServer/39", fields: ["SSL", "geometry → centroid"] },
      ]}
      notes="Regex over OWNERNAME catches 'Government of X', 'Royal Y', 'Embassy of Z', etc. Group by country (with manual name aliases), centroid → flag location, sum NEWTOTAL → flag size."
    />,

    <Slide key="tax-exempt">
      <SlideTitle eyebrow="Tax-exempt land">What&apos;s not on the rolls.</SlideTitle>
      <div className="mt-4">
        {citywideClusters.length > 0 ? <TaxExemptMap clusters={citywideClusters} /> : <Placeholder />}
      </div>
    </Slide>,
    <DataNote
      key="tax-exempt-data"
      vizTitle="DC's tax-exempt land"
      layers={[
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "/FeatureServer/53", fields: ["SSL", "USECODE", "NEWTOTAL"] },
        { name: "Tax Lots", path: "/FeatureServer/39", fields: ["SSL", "geometry → centroid"] },
        { name: "Neighborhood Clusters", path: "MapServer/17", fields: ["NAME", "NBH_NAMES", "geometry"] },
      ]}
      notes="USECODE 081-089 = special-purpose (religious / educational / govt / embassy / etc.). Spatial-join parcels to clusters, then sum NEWTOTAL → cluster-level exempt share."
    />,

    <Slide key="big-sales">
      <SlideTitle eyebrow="Biggest deals">Top sales since Jan 2025.</SlideTitle>
      <div className="mt-4">
        {topSales.length > 0 ? <BiggestSalesMap rows={topSales} limit={40} /> : <Placeholder />}
      </div>
    </Slide>,
    <DataNote
      key="big-sales-data"
      vizTitle="Biggest DC sales since Jan 2025"
      layers={[
        { name: "Property Sales (Computer Assisted Mass Appraisal)", path: "/FeatureServer/57", fields: ["SSL", "SALE_DATE", "SALE_PRICE", "QUALIFIED"] },
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "/FeatureServer/53", fields: ["SSL", "USECODE", "PREMISEADD"] },
        { name: "Tax Lots", path: "/FeatureServer/39", fields: ["SSL", "geometry → centroid"] },
      ]}
      notes="Filter SALE_DATE >= 2025-01-01, QUALIFIED = 'Q'. Sort by SALE_PRICE desc. Bubble size scales with sqrt(SALE_PRICE) so area is proportional to dollars."
    />,

    // ═══ PART THREE ══════════════════════════════════════
    <SectionDivider
      key="div-3"
      number="Three"
      title="Here's a project I built with it."
      subtitle="Sliced by time and geography to ask: what's happening in DC's housing market?"
    />,

    <Slide key="project-goal">
      <SlideTitle eyebrow="The goal">Understand sales activity since 2020.</SlideTitle>
      <SlideBody>
        <p className="max-w-3xl">
          The CAMA Property Sales table has every qualified sale on file. Pull it,
          filter, aggregate, and you can see what&apos;s happened to the DC market
          over the rate-hike cycle, the WFH shift, and the federal labor changes
          since 2020 — without anyone&apos;s commentary in the way.
        </p>
        <div className="mt-8 grid gap-3 grid-cols-2 sm:grid-cols-4 max-w-3xl">
          <Stat label="Total sales pulled" value={summary.total_sales.toLocaleString()} />
          <Stat label="Years covered" value="2020-now" />
          <Stat label="LOC" value="~600" />
          <Stat label="Dependencies" value="0 ext." sub="(stdlib + Next.js)" />
        </div>
      </SlideBody>
    </Slide>,

    <Slide key="res-monthly">
      <SlideTitle eyebrow="What the data shows">Residential sales by month.</SlideTitle>
      <div className="mt-4">
        <SingleVolumeChart
          monthly={monthly}
          series="residential"
          title="Residential sales by month"
          description="Thin line: raw monthly · thick line: 12-month trailing average"
          color="var(--chart-1)"
        />
      </div>
    </Slide>,
    <DataNote
      key="res-monthly-data"
      vizTitle="Residential sales by month"
      layers={[
        { name: "Property Sales (Computer Assisted Mass Appraisal)", path: "/FeatureServer/57", fields: ["SSL", "SALE_DATE", "SALE_PRICE", "QUALIFIED"] },
        { name: "ITSPE (Integrated Tax System Public Extract)", path: "/FeatureServer/53", fields: ["SSL", "USECODE → category"] },
      ]}
      notes="Filter QUALIFIED = 'Q', SALE_PRICE > 0, date ≥ 2020-01-01. Residential = use codes 011-029. Bucket by month, compute 12-month rolling average. Drop the current month when it's not complete."
    />,

    <Slide key="sales-map">
      <SlideTitle eyebrow="What the data shows">Where the activity is happening.</SlideTitle>
      <div className="mt-4">
        <SalesMap clusters={clustersGeo} />
      </div>
    </Slide>,
    <DataNote
      key="sales-map-data"
      vizTitle="Sales by neighborhood, year by year"
      layers={[
        { name: "Property Sales (Computer Assisted Mass Appraisal)", path: "/FeatureServer/57", fields: ["SSL", "SALE_DATE", "SALE_PRICE", "QUALIFIED"] },
        { name: "Tax Lots", path: "/FeatureServer/39", fields: ["SSL", "geometry → centroid"] },
        { name: "Neighborhood Clusters", path: "MapServer/17", fields: ["NAME", "NBH_NAMES", "geometry"] },
      ]}
      notes="Spatial-join sale centroids to cluster polygons, then count by year × cluster. Global color scale (max across all years) so the 2020 → 2025 decline shows up visually when you scrub through."
    />,

    <Slide key="caveats">
      <SlideTitle eyebrow="A note on limits">What we couldn&apos;t see.</SlideTitle>
      <SlideBody>
        <div className="grid gap-6 md:grid-cols-2 max-w-4xl">
          <div>
            <div className="text-sm uppercase tracking-wide text-muted-foreground mb-2">It tells you</div>
            <ul className="space-y-1.5 text-base">
              <li>· What transacted, when, at what price</li>
              <li>· Who owns what right now</li>
              <li>· Use codes, building age + size, lot size</li>
              <li>· Geographic location of every parcel</li>
            </ul>
          </div>
          <div>
            <div className="text-sm uppercase tracking-wide text-muted-foreground mb-2">It doesn&apos;t tell you</div>
            <ul className="space-y-1.5 text-base">
              <li>· Buyer / grantee names on historical sales</li>
              <li>· Rental and lease activity</li>
              <li>· Vacancy or occupancy</li>
              <li>· What&apos;s currently listed</li>
            </ul>
          </div>
        </div>
        <p className="mt-8 max-w-3xl text-muted-foreground">
          For the right-hand column you&apos;d need the DC Recorder of Deeds subscription
          ($175 / month), MLS access, or CoStar. All paid.
        </p>
      </SlideBody>
    </Slide>,

    // ═══ PART FOUR ═══════════════════════════════════════
    <SectionDivider
      key="div-4"
      number="Four"
      title="Other things you could build."
      subtitle="A short list of projects that fall out of the same data, in case anyone wants to pick one up."
    />,

    <Slide key="ideas">
      <SlideTitle eyebrow="Ideas">Things You Could Make.</SlideTitle>
      <SlideBody>
        <div className="grid gap-3 sm:grid-cols-2 max-w-5xl mt-2">
          <Idea
            title="Surface parking lot map"
            desc={<>Map every <b>surface parking lot</b> in DC. Headline: <i>X acres within Y miles of the Capitol</i>.</>}
          />
          <Idea
            title="Church-to-condo tracker"
            desc={<>Religious parcels that <b>flipped to residential</b>. Real ongoing trend.</>}
          />
          <Idea
            title="Vacant &amp; blighted dashboard"
            desc={<>DC&apos;s official <b>vacant/blighted</b> registry, mapped. Useful for ANCs and housing reporters.</>}
          />
          <Idea
            title="Tax-sale tracker"
            desc={<>Annual <b>tax delinquency</b> list × parcel data. Especially interesting when a tax-exempt org appears.</>}
          />
          <Idea
            title="Sales near Metro"
            desc={<>Cross-join with <b>WMATA stations</b>. What sold within walking distance of every stop.</>}
          />
          <Idea
            title="Event venue finder"
            desc={<>Public search for <b>event spaces</b> — filter by neighborhood, size, type.</>}
          />
        </div>
      </SlideBody>
    </Slide>,

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

    <Slide key="close">
      <SlideTitle eyebrow="If you want to try it">Where to start.</SlideTitle>
      <SlideBody>
        <div className="space-y-4 max-w-3xl">
          <Item title="DC's catalog">
            <code className="text-foreground bg-muted px-1.5 py-0.5 rounded text-sm">opendata.dc.gov/api/feed/dcat-us/1.1.json</code>{" "}
            lists every dataset.
          </Item>
          <Item title="The base server for parcel data">
            <code className="text-foreground bg-muted px-1.5 py-0.5 rounded text-sm">maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA</code>
          </Item>
          <Item title="This repo">
            <code className="text-foreground bg-muted px-1.5 py-0.5 rounded text-sm">dc-realestate-2026</code>{" "}
            — Python pulls + Next.js site. ~600 lines total.
          </Item>
        </div>
      </SlideBody>
    </Slide>,
  ];

  return <Deck slides={slides} />;
}

function Placeholder() {
  return (
    <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">
      (Data not yet generated — run <code>pipeline/pull_citywide.py</code>.)
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

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border p-4">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

function TitleStat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="text-3xl font-semibold tabular-nums">{value}</div>
      <div className="text-sm text-muted-foreground uppercase tracking-wide">{label}</div>
    </div>
  );
}

function AgendaItem({ num, title, desc }: { num: string; title: string; desc: string }) {
  return (
    <div className="flex gap-8">
      <div className="text-3xl font-semibold text-muted-foreground/60 tabular-nums w-24 shrink-0">
        {num}
      </div>
      <div>
        <div className="text-xl font-semibold tracking-tight">{title}</div>
        <div className="mt-1.5 text-base text-muted-foreground">{desc}</div>
      </div>
    </div>
  );
}
