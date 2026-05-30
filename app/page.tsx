import { promises as fs } from "fs";
import path from "path";
import Link from "next/link";
import { Presentation } from "lucide-react";
import { SummaryCards } from "@/components/SummaryCards";
import { SingleVolumeChart } from "@/components/SingleVolumeChart";
import { UseTypeHeatmap } from "@/components/UseTypeHeatmap";
import { SalesMap } from "@/components/SalesMap";
import type { Summary, MonthlyRow, ByUseRow, ClusterGeo } from "@/lib/types";

async function loadJson<T>(name: string): Promise<T> {
  const p = path.join(process.cwd(), "public", name);
  return JSON.parse(await fs.readFile(p, "utf-8")) as T;
}

export default async function HomePage() {
  const [summary, monthly, byUse, clustersGeo] = await Promise.all([
    loadJson<Summary>("summary.json"),
    loadJson<MonthlyRow[]>("monthly.json"),
    loadJson<ByUseRow[]>("by_use.json"),
    loadJson<ClusterGeo[]>("clusters_geo.json"),
  ]);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <header className="mb-8 flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              DC Real Estate 2026
            </h1>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Citywide qualified arms-length sales since January 2020. Pulled from the
              DC Office of Tax &amp; Revenue&apos;s CAMA dataset. No proprietary data;
              fully reproducible.
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Data through {summary.last_sale} · generated {summary.generated_at}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/slides/short"
              className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
            >
              <Presentation className="size-4" />
              5-min deck
            </Link>
            <Link
              href="/slides"
              className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
            >
              Full deck
            </Link>
          </div>
        </header>

        <section className="mb-8">
          <SummaryCards summary={summary} />
        </section>

        <section className="mb-8">
          <SingleVolumeChart
            monthly={monthly}
            series="residential"
            title="Residential sales by month"
            description="Thin line: monthly · thick line: 12-month trailing average"
            color="var(--chart-1)"
          />
        </section>

        <section className="mb-8">
          <SingleVolumeChart
            monthly={monthly}
            series="commercial"
            title="Commercial sales by month"
            description="Thin line: monthly · thick line: 12-month trailing average"
            color="var(--chart-3)"
          />
        </section>

        <section className="mb-8">
          <SalesMap clusters={clustersGeo} />
        </section>

        <section className="mb-8">
          <UseTypeHeatmap rows={byUse} />
        </section>

        <footer className="mt-12 border-t pt-6 space-y-2 text-xs text-muted-foreground">
          <p>
            Source: DC Office of Tax &amp; Revenue (CAMA + ITSPE), via
            maps2.dcgis.dc.gov. Qualified sales only (DC&apos;s &quot;Q&quot; flag) with
            non-zero prices. $0 / unqualified transfers excluded. The current month is
            also excluded when it is incomplete. 2026 figures in the heatmap are
            annualized from YTD data.
          </p>
          <p>
            <strong>On data freshness:</strong> CAMA updates daily but with a recording lag.
            Anything through 2025 is fully settled. The most recent ~3 months are typically
            80–95% complete and will tick up as more deeds are processed. The numbers in
            this dashboard will edge upward over the next 60 days as Jan–Mar 2026 fill in.
          </p>
        </footer>
      </div>
    </div>
  );
}
