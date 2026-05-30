"use client";

import { useMemo } from "react";
import L from "leaflet";
import { MapContainer, TileLayer, Marker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

type ForeignParcel = {
  owner: string;
  lat: number;
  lon: number;
  assessed: number;
  address: string;
};

// Map owner-name patterns → [pretty country name, ISO-2 code].
const COUNTRY_TABLE: Array<[RegExp, string, string]> = [
  [/CAMEROON/i, "Cameroon", "CM"],
  [/INDIA/i, "India", "IN"],
  [/ARGENTINA/i, "Argentina", "AR"],
  [/TRINIDAD/i, "Trinidad & Tobago", "TT"],
  [/MOROCCO/i, "Morocco", "MA"],
  [/ROYAL SIAMESE|THAI/i, "Thailand", "TH"],
  [/KOREA/i, "South Korea", "KR"],
  [/POLAND/i, "Poland", "PL"],
  [/EGYPT/i, "Egypt", "EG"],
  [/MALAYSIA/i, "Malaysia", "MY"],
  [/GUYANA/i, "Guyana", "GY"],
  [/CHILE/i, "Chile", "CL"],
  [/PHILIPPINES/i, "Philippines", "PH"],
  [/MEXICO|UNITED MEXICAN STATES/i, "Mexico", "MX"],
  [/JAPAN/i, "Japan", "JP"],
  [/UNITED KINGDOM/i, "United Kingdom", "GB"],
  [/FRANCE/i, "France", "FR"],
  [/GERMANY/i, "Germany", "DE"],
  [/CANADA/i, "Canada", "CA"],
  [/ITALY/i, "Italy", "IT"],
  [/SPAIN/i, "Spain", "ES"],
  [/RUSSIA/i, "Russia", "RU"],
  [/\bCHINA\b/i, "China", "CN"],
  [/IRELAND/i, "Ireland", "IE"],
  [/BRAZIL/i, "Brazil", "BR"],
  [/COMMONWEALTH OF AUSTRALIA|AUSTRALIA/i, "Australia", "AU"],
  [/SAUDI ARABIA/i, "Saudi Arabia", "SA"],
  [/QATAR/i, "Qatar", "QA"],
  [/UNITED ARAB EMIRATES|UAE/i, "UAE", "AE"],
  [/KUWAIT/i, "Kuwait", "KW"],
  [/BAHRAIN/i, "Bahrain", "BH"],
  [/OMAN/i, "Oman", "OM"],
  [/JORDAN/i, "Jordan", "JO"],
  [/LEBANON/i, "Lebanon", "LB"],
  [/ISRAEL/i, "Israel", "IL"],
  [/TURKEY|T[UÜ]RKIYE/i, "Turkey", "TR"],
  [/IRAN/i, "Iran", "IR"],
  [/PAKISTAN/i, "Pakistan", "PK"],
  [/BANGLADESH/i, "Bangladesh", "BD"],
  [/SRI LANKA/i, "Sri Lanka", "LK"],
  [/NEPAL/i, "Nepal", "NP"],
  [/MYANMAR|BURMA/i, "Myanmar", "MM"],
  [/VIETNAM/i, "Vietnam", "VN"],
  [/INDONESIA/i, "Indonesia", "ID"],
  [/SINGAPORE/i, "Singapore", "SG"],
  [/NEW ZEALAND/i, "New Zealand", "NZ"],
  [/HUNGARY/i, "Hungary", "HU"],
  [/AUSTRIA/i, "Austria", "AT"],
  [/BELGIUM/i, "Belgium", "BE"],
  [/NETHERLANDS|HOLLAND/i, "Netherlands", "NL"],
  [/SWEDEN/i, "Sweden", "SE"],
  [/NORWAY/i, "Norway", "NO"],
  [/DENMARK/i, "Denmark", "DK"],
  [/FINLAND/i, "Finland", "FI"],
  [/SWITZERLAND/i, "Switzerland", "CH"],
  [/PORTUGAL/i, "Portugal", "PT"],
  [/GREECE/i, "Greece", "GR"],
  [/CZECH/i, "Czech Republic", "CZ"],
  [/SLOVAK/i, "Slovakia", "SK"],
  [/CROATIA/i, "Croatia", "HR"],
  [/SERBIA/i, "Serbia", "RS"],
  [/SLOVENIA/i, "Slovenia", "SI"],
  [/ROMANIA/i, "Romania", "RO"],
  [/BULGARIA/i, "Bulgaria", "BG"],
  [/UKRAINE/i, "Ukraine", "UA"],
  [/BELARUS/i, "Belarus", "BY"],
  [/LITHUANIA/i, "Lithuania", "LT"],
  [/LATVIA/i, "Latvia", "LV"],
  [/ESTONIA/i, "Estonia", "EE"],
  [/SOUTH AFRICA/i, "South Africa", "ZA"],
  [/NIGERIA/i, "Nigeria", "NG"],
  [/KENYA/i, "Kenya", "KE"],
  [/ETHIOPIA/i, "Ethiopia", "ET"],
  [/GHANA/i, "Ghana", "GH"],
  [/SENEGAL/i, "Senegal", "SN"],
  [/MOZAMBIQUE/i, "Mozambique", "MZ"],
  [/COLOMBIA/i, "Colombia", "CO"],
  [/PERU/i, "Peru", "PE"],
  [/VENEZUELA/i, "Venezuela", "VE"],
  [/ECUADOR/i, "Ecuador", "EC"],
  [/URUGUAY/i, "Uruguay", "UY"],
  [/COSTA RICA/i, "Costa Rica", "CR"],
  [/PANAMA/i, "Panama", "PA"],
  [/HAITI/i, "Haiti", "HT"],
  [/JAMAICA/i, "Jamaica", "JM"],
];

function lookupCountry(owner: string): { name: string; code: string } | null {
  for (const [pat, name, code] of COUNTRY_TABLE) {
    if (pat.test(owner)) return { name, code };
  }
  return null;
}

function flagEmoji(code: string): string {
  return code
    .toUpperCase()
    .split("")
    .map((c) => String.fromCodePoint(127397 + c.charCodeAt(0)))
    .join("");
}

function fmtMoney(n: number) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(0)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

export function ForeignFlagMapImpl({ parcels }: { parcels: ForeignParcel[] }) {
  // Group by country, compute aggregate stats + centroid.
  const byCountry = useMemo(() => {
    const map = new Map<string, {
      name: string; code: string;
      total_assessed: number; parcel_count: number;
      lat_sum: number; lon_sum: number;
    }>();
    for (const p of parcels) {
      const c = lookupCountry(p.owner);
      if (!c) continue;
      const cur = map.get(c.code) || {
        name: c.name, code: c.code,
        total_assessed: 0, parcel_count: 0,
        lat_sum: 0, lon_sum: 0,
      };
      cur.total_assessed += p.assessed;
      cur.parcel_count += 1;
      cur.lat_sum += p.lat;
      cur.lon_sum += p.lon;
      map.set(c.code, cur);
    }
    return Array.from(map.values()).map((c) => ({
      ...c,
      lat: c.lat_sum / c.parcel_count,
      lon: c.lon_sum / c.parcel_count,
    }));
  }, [parcels]);

  const maxAssessed = Math.max(...byCountry.map((c) => c.total_assessed), 1);
  const totalAssessed = byCountry.reduce((s, c) => s + c.total_assessed, 0);

  // Flag font size: scale by sqrt of assessed value for visual area ∝ $.
  function flagSize(assessed: number): number {
    const t = Math.sqrt(assessed / maxAssessed);
    return Math.max(16, Math.min(64, 16 + t * 48));
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Foreign government real estate in DC</CardTitle>
        <CardDescription>
          Each flag is one country&apos;s embassy / chancery footprint, placed at the
          centroid of their DC parcels. Flag size scales with total assessed
          value — bigger flag, bigger holdings. ({byCountry.length} countries,
          {" "}{fmtMoney(totalAssessed)} total assessed.)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[520px] w-full rounded-md overflow-hidden border">
          <MapContainer
            center={[38.917, -77.045]}
            zoom={13}
            scrollWheelZoom={false}
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {byCountry.map((c) => {
              const size = flagSize(c.total_assessed);
              const icon = L.divIcon({
                className: "",
                html: `<div style="font-size:${size}px;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,.4));cursor:default">${flagEmoji(c.code)}</div>`,
                iconSize: [size, size],
                iconAnchor: [size / 2, size / 2],
              });
              return (
                <Marker key={c.code} position={[c.lat, c.lon]} icon={icon}>
                  <Tooltip direction="top" offset={[0, -size / 2]}>
                    <div className="text-xs">
                      <div className="font-semibold">{flagEmoji(c.code)} {c.name}</div>
                      <div>{fmtMoney(c.total_assessed)} · {c.parcel_count} parcel{c.parcel_count === 1 ? "" : "s"}</div>
                    </div>
                  </Tooltip>
                </Marker>
              );
            })}
          </MapContainer>
        </div>
      </CardContent>
    </Card>
  );
}
