"use client";

import dynamic from "next/dynamic";
import type { TopSale } from "@/lib/types";

const Impl = dynamic(() => import("./BiggestSalesMapImpl").then(m => m.BiggestSalesMapImpl), {
  ssr: false,
  loading: () => (
    <div className="rounded-md border bg-card p-6 text-sm text-muted-foreground">
      Loading map…
    </div>
  ),
});

export function BiggestSalesMap({ rows, limit = 50 }: { rows: TopSale[]; limit?: number }) {
  return <Impl rows={rows} limit={limit} />;
}
