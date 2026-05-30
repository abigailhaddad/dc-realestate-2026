import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

type Owner = {
  owner: string;
  parcels: number;
  assessed_total: number;
};

const FOREIGN_PATTERNS = [
  /^GOVERNMENT OF/i,
  /^EMBASSY/i,
  /^FEDERAL REPUBLIC OF/i,
  /\bREPUBLIC OF\b/i,
  /^ROYAL/i,
  /^KINGDOM OF/i,
  /^DEMOCRATIC REPUBLIC/i,
  /^STATE OF (?!THE WORLD)/i,  // exclude generic
  /^ARAB REPUBLIC/i,
  /AMBASSADOR/i,
];

const COUNTRY_SHORT: Array<[RegExp, string]> = [
  [/CAMEROON/i, "Cameroon"], [/INDIA/i, "India"], [/ARGENTINA/i, "Argentina"],
  [/TRINIDAD/i, "Trinidad & Tobago"], [/MOROCCO/i, "Morocco"],
  [/ROYAL SIAMESE|THAI/i, "Thailand"], [/KOREA/i, "South Korea"],
  [/POLAND/i, "Poland"], [/EGYPT/i, "Egypt"], [/MALAYSIA/i, "Malaysia"],
  [/GUYANA/i, "Guyana"], [/CHILE/i, "Chile"], [/PHILIPPINES/i, "Philippines"],
  [/MEXICO|UNITED MEXICAN STATES/i, "Mexico"], [/JAPAN/i, "Japan"], [/UNITED KINGDOM/i, "United Kingdom"],
  [/FRANCE/i, "France"], [/GERMANY/i, "Germany"], [/CANADA/i, "Canada"],
  [/ITALY/i, "Italy"], [/SPAIN/i, "Spain"], [/RUSSIA/i, "Russia"],
  [/CHINA/i, "China"], [/IRELAND/i, "Ireland"], [/BRAZIL/i, "Brazil"],
  [/COMMONWEALTH OF AUSTRALIA|AUSTRALIA/i, "Australia"], [/SAUDI ARABIA/i, "Saudi Arabia"],
  [/QATAR/i, "Qatar"], [/UNITED ARAB EMIRATES|UAE/i, "United Arab Emirates"],
  [/KUWAIT/i, "Kuwait"], [/BAHRAIN/i, "Bahrain"], [/OMAN/i, "Oman"],
  [/JORDAN/i, "Jordan"], [/LEBANON/i, "Lebanon"], [/ISRAEL/i, "Israel"],
  [/TURKEY|REPUBLIC OF T[UÜ]RKIYE/i, "Turkey"], [/IRAN/i, "Iran"],
  [/PAKISTAN/i, "Pakistan"], [/BANGLADESH/i, "Bangladesh"],
  [/SRI LANKA/i, "Sri Lanka"], [/NEPAL/i, "Nepal"], [/MYANMAR|BURMA/i, "Myanmar"],
  [/VIETNAM/i, "Vietnam"], [/INDONESIA/i, "Indonesia"], [/SINGAPORE/i, "Singapore"],
  [/NEW ZEALAND/i, "New Zealand"], [/HUNGARY/i, "Hungary"], [/AUSTRIA/i, "Austria"],
  [/BELGIUM/i, "Belgium"], [/NETHERLANDS|HOLLAND/i, "Netherlands"],
  [/SWEDEN/i, "Sweden"], [/NORWAY/i, "Norway"], [/DENMARK/i, "Denmark"],
  [/FINLAND/i, "Finland"], [/SWITZERLAND/i, "Switzerland"], [/PORTUGAL/i, "Portugal"],
  [/GREECE/i, "Greece"], [/CZECH/i, "Czech Republic"], [/SLOVAK/i, "Slovakia"],
  [/CROATIA/i, "Croatia"], [/SERBIA/i, "Serbia"], [/SLOVENIA/i, "Slovenia"],
  [/ROMANIA/i, "Romania"], [/BULGARIA/i, "Bulgaria"], [/UKRAINE/i, "Ukraine"],
  [/BELARUS/i, "Belarus"], [/LITHUANIA/i, "Lithuania"], [/LATVIA/i, "Latvia"],
  [/ESTONIA/i, "Estonia"], [/SOUTH AFRICA/i, "South Africa"],
  [/NIGERIA/i, "Nigeria"], [/KENYA/i, "Kenya"], [/ETHIOPIA/i, "Ethiopia"],
  [/GHANA/i, "Ghana"], [/SENEGAL/i, "Senegal"], [/MOZAMBIQUE/i, "Mozambique"],
  [/COLOMBIA/i, "Colombia"], [/PERU/i, "Peru"], [/VENEZUELA/i, "Venezuela"],
  [/ECUADOR/i, "Ecuador"], [/URUGUAY/i, "Uruguay"], [/COSTA RICA/i, "Costa Rica"],
  [/PANAMA/i, "Panama"], [/HAITI/i, "Haiti"], [/JAMAICA/i, "Jamaica"],
];

// Owners that match the foreign-gov regex but aren't actually foreign governments.
const EXCLUDE = new Set([
  "AMBASSADOR INC",
  "ROYAL CARRIBEAN CRUISES LTD",
]);

function isExcluded(owner: string) {
  return EXCLUDE.has(owner.toUpperCase().trim());
}

function shortCountry(owner: string) {
  for (const [pat, name] of COUNTRY_SHORT) {
    if (pat.test(owner)) return name;
  }
  // Strip leading boilerplate, then title-case.
  const stripped = owner
    .replace(/^(GOVERNMENT OF THE|GOVERNMENT OF|FEDERAL REPUBLIC OF|KINGDOM OF|REPUBLIC OF|ROYAL|EMBASSY OF|COMMONWEALTH OF|STATE OF|DEMOCRATIC REPUBLIC OF|ARAB REPUBLIC OF)\s+/i, "")
    .replace(/\b(GOVERNMENT|EMBASSY|CHANCERY|MINISTRY|REPUBLIC)\b/gi, "")
    .trim();
  // Title-case
  return stripped.replace(/\w\S*/g, (w) => w[0] + w.slice(1).toLowerCase());
}

function fmtMoney(n: number) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(0)}M`;
  return `$${n.toLocaleString()}`;
}

export function ForeignGov({ owners }: { owners: Owner[] }) {
  const allForeign = owners
    .filter((o) =>
      o.owner !== "UNITED STATES OF AMERICA" &&
      !isExcluded(o.owner) &&
      FOREIGN_PATTERNS.some((p) => p.test(o.owner)),
    )
    .map((o) => ({ ...o, country: shortCountry(o.owner) }));

  // Aggregate by country (multiple owner strings can map to same country)
  const byCountry = new Map<string, { country: string; parcels: number; assessed_total: number }>();
  for (const o of allForeign) {
    const cur = byCountry.get(o.country) || { country: o.country, parcels: 0, assessed_total: 0 };
    cur.parcels += o.parcels;
    cur.assessed_total += o.assessed_total;
    byCountry.set(o.country, cur);
  }
  const foreign = Array.from(byCountry.values())
    .sort((a, b) => b.assessed_total - a.assessed_total);

  const totalValue = foreign.reduce((s, o) => s + o.assessed_total, 0);
  const totalParcels = foreign.reduce((s, o) => s + o.parcels, 0);
  const top = foreign[0];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Foreign government landholdings in DC</CardTitle>
        <CardDescription>
          Parcels owned by &quot;Government of X&quot; / &quot;Embassy of X&quot; / &quot;Royal Y&quot; etc.,
          extracted by regex over ITSPE&apos;s OWNERNAME field.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {top && (
          <div className="mb-5 grid gap-3 grid-cols-1 sm:grid-cols-3">
            <HeadStat value={fmtMoney(totalValue)} label="Total assessed value" />
            <HeadStat value={foreign.length.toString()} label="Countries" sub={`${totalParcels} parcels`} />
            <HeadStat value={top.country} label="Biggest holder" sub={fmtMoney(top.assessed_total)} />
          </div>
        )}
        <div className="grid gap-2 grid-cols-1 sm:grid-cols-2">
          {foreign.slice(0, 16).map((o, i) => (
            <div key={i} className="flex items-baseline justify-between gap-3 py-1.5 border-b last:border-b-0">
              <div>
                <div className="font-medium text-sm">{o.country}</div>
                <div className="text-xs text-muted-foreground">
                  {o.parcels} parcel{o.parcels === 1 ? "" : "s"}
                </div>
              </div>
              <div className="text-sm tabular-nums font-semibold">{fmtMoney(o.assessed_total)}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function HeadStat({ value, label, sub }: { value: string; label: string; sub?: string }) {
  return (
    <div className="rounded-lg border p-4 bg-accent/30">
      <div className="text-xl font-semibold tabular-nums">{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground mt-1">{label}</div>
      {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  );
}
