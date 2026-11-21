# Daily price-anomaly screen

Last run: 2026-11-21 18:55 UTC. Covers sales from 2025-01-01 through each jurisdiction's most recent data pull (below) in DC, Arlington (VA), Montgomery + Prince George's (MD), and Fairfax (VA). Full methodology: [`docs/overpriced_sales.md`](./overpriced_sales.md).

**This pipeline flags transactions, never people.** No owner, buyer, or seller name is used anywhere in it. A flag is a reason to look, not a finding -- most flagged sales turn out to have an ordinary explanation.

## As of this run

| Jurisdiction | Latest sale in the pull | 2025+ sales on file | New since last run |
|---|---|---|---|
| DC | 2026-11-12 | 17,174 | +0 |
| Arlington, VA | 2026-11-19 | 5,327 | +9 |
| Montgomery + Prince George's, MD | 2026-10-29 | 67,759 | +0 |
| Fairfax, VA | 2026-09-15 | 25,676 | +0 |

**115,936 sales on file since 2025-01-01 across all four areas (+9 new since the last run).**

## Flagged as price outliers

**2,045 sale/screen combinations flagged** across every screen this run (a single sale can be flagged by more than one screen). **940 have an automated ordinary explanation** (new construction, a documented construction/renovation permit, consistent with the property's own sale history, a farm or large-lot assessment, or a comparable public listing). **1,105 remain unexplained by anything this pipeline checks automatically.**

Of those 1,105, **26 are new since the last run** (not already unexplained yesterday).

| Jurisdiction | Flagged (sale/screen combos) | Unexplained |
|---|---|---|
| DC | 1407 | 913 |
| Montgomery, MD | 306 | 73 |
| Prince George's, MD | 238 | 91 |
| Arlington, VA | 76 | 10 |
| Fairfax, VA | 18 | 18 |

### What this run does and does not check automatically

- **DC house sales** get the full automated chain: assessment-ratio screen + comps screen, then an own-sale-history check, then a manual listing check IF one has already been recorded locally (listing checks require a web search and are not run in CI -- see `pipeline/listing_checks.py`). On a from-scratch run (e.g. this repo's CI), most DC house candidates will show as `unchecked`, not `cleared`: that means no listing search has been done yet, not that the sale is suspicious.
- **DC condos, multifamily, vacant, parking, mixed, and multi-property sales** flagged by the assessment-ratio screen get NO further automated check in this pipeline -- they are listed below as unexplained by definition.
- **DC's three pattern screens** (comps both ways, OTR 'Unusual' code, bought-high-resold-lower) each carry their own inline explanation check (permits, new construction, bought-new).
- **Arlington / Maryland** comps candidates get own-sale-history, farm/large-lot (MD), new-construction, and construction-permit checks. The county-coded 'not listed MLS' list (Arlington) gets none of those checks at all.
- **Fairfax** relies on the county assessor's own 'atypical sale' coding rather than a comps screen; everything in `kept` has already had new-construction and remodel-year set-asides applied, so everything listed below is genuinely unexplained by this chain.

## Newly flagged since the last run

Sales that are unexplained today and were NOT already unexplained on the previous run (i.e. either new sales, or newly flagged by a screen). This is the section worth reading daily; everything below it is the full accumulated backlog.

| Jurisdiction | Screen | Date | Price | Address | Why flagged |
|---|---|---|---|---|---|
| DC | assessment + comps (house) | 2026-09-03 | $11,000,000 | 2930 CHAIN BRIDGE RD NW WASHINGTON DC 20016-3408 | 3.8x the neighborhood peer price/assessment ratio, $8,524,050 over assessment |
| DC | assessment + comps (house) | 2026-01-22 | $5,999,000 | 4849 KEMBLE PL NW WASHINGTON DC 20007-1052 | 2.1x the neighborhood peer price/assessment ratio, $3,450,690 over assessment |
| DC | assessment + comps (house) | 2025-09-03 | $5,000,000 | 4414 W ST NW WASHINGTON DC 20007 | 1.7x comps' $/sqft, 12 comparables |
| DC | assessment + comps (house) | 2025-12-22 | $4,500,000 | 3003 AUDUBON TER NW WASHINGTON DC 20008 | 1.62x comps' $/sqft, 10 comparables |
| DC | assessment + comps (house) | 2026-09-03 | $3,450,000 | 4631 49TH ST NW WASHINGTON DC 20016-4320 | 2.6x the neighborhood peer price/assessment ratio, $2,303,660 over assessment |
| DC | assessment + comps (house) | 2025-01-22 | $3,225,000 | 622 MASSACHUSETTS AVE NE WASHINGTON DC 20002-6006 | 1.65x comps' $/sqft, 16 comparables |
| DC | assessment + comps (house) | 2025-01-13 | $2,950,000 | 1519 SWANN ST NW WASHINGTON DC 20009 | 1.88x comps' $/sqft, 16 comparables |
| DC | assessment + comps (house) | 2026-04-15 | $2,925,000 | 1213 O ST NW WASHINGTON DC 20005 | 1.49x comps' $/sqft, 16 comparables |
| DC | assessment + comps (house) | 2026-07-08 | $2,875,000 | 1308 CORCORAN ST NW WASHINGTON DC 20009 | 2.36x comps' $/sqft, 49 comparables |
| DC | assessment + comps (house) | 2025-03-07 | $2,800,000 | 3623 R ST NW WASHINGTON DC 20007 | 1.34x comps' $/sqft, 10 comparables |
| DC | assessment + comps (house) | 2026-08-14 | $2,750,000 | 4905 45TH ST NW WASHINGTON DC 20016 | 2.0x the neighborhood peer price/assessment ratio, $1,554,750 over assessment |
| DC | assessment + comps (house) | 2026-10-30 | $2,725,000 | 4528 49TH ST NW WASHINGTON DC 20016-4366 | 2.0x the neighborhood peer price/assessment ratio, $1,557,010 over assessment |
| DC | assessment + comps (house) | 2025-10-22 | $2,625,000 | 4900 PALISADE LN NW WASHINGTON DC 20016 | 1.3x comps' $/sqft, 10 comparables |
| DC | assessment + comps (house) | 2025-06-23 | $2,500,000 | 333 12TH ST NE WASHINGTON DC 20002-6319 | 1.84x comps' $/sqft, 60 comparables |
| DC | assessment + comps (house) | 2026-06-25 | $2,500,000 | 1324 35TH ST NW WASHINGTON DC 20007 | 1.42x comps' $/sqft, 19 comparables |
| DC | assessment + comps (house) | 2026-04-21 | $2,495,000 | 153 NORTH CAROLINA AVE SE WASHINGTON DC 20003-1846 | 1.82x comps' $/sqft, 31 comparables |
| DC | assessment + comps (house) | 2026-06-04 | $2,450,000 | 4910 BRANDYWINE ST NW WASHINGTON DC 20016 | 1.4x comps' $/sqft, 17 comparables |
| DC | assessment + comps (house) | 2026-05-13 | $2,421,000 | 3410 RODMAN ST NW WASHINGTON DC 20008 | 1.38x comps' $/sqft, 15 comparables |
| DC | assessment + comps (house) | 2026-01-15 | $1,950,000 | 1509 CAROLINE ST NW WASHINGTON DC 20009 | 2.2x the neighborhood peer price/assessment ratio, $1,105,620 over assessment |
| DC | assessment + comps (house) | 2026-07-09 | $1,875,000 | 1227 E ST SE WASHINGTON DC 20003-2221 | 1.36x comps' $/sqft, 69 comparables |
| DC | assessment + comps (house) | 2025-06-11 | $1,525,000 | 7703 12TH ST NW WASHINGTON DC 20012 | 1.33x comps' $/sqft, 25 comparables |
| DC | assessment + comps (house) | 2025-01-09 | $1,200,000 | 615 KENNEDY ST NW WASHINGTON DC 20011 | 1.88x comps' $/sqft, 14 comparables |
| DC | assessment + comps (house) | 2026-08-05 | $975,000 | 2203 CHANNING ST NE WASHINGTON DC 20018 | 2.5x the neighborhood peer price/assessment ratio, $610,500 over assessment |
| DC | assessment + comps (house) | 2025-05-21 | $745,000 | 1316 31ST PL SE WASHINGTON DC 20020-3635 | 1.53x comps' $/sqft, 13 comparables |
| DC | assessment + comps (house) | 2026-09-30 | $650,000 | 2553 ALABAMA AVE SE WASHINGTON DC 20020-3224 | 2.2x the neighborhood peer price/assessment ratio, $359,380 over assessment |
| DC | assessment + comps (house) | 2026-07-27 | $519,000 | 2719 HARTFORD ST SE WASHINGTON DC 20020-2728 | 1.39x comps' $/sqft, 24 comparables |

## All unexplained candidates (largest first)

Address, price, date, and why each was flagged, for all 1,105 sale/screen combinations this run could not automatically explain. No owner, buyer, or seller name is included or was looked up for this list. Showing the 60 largest by price; the remaining 1,045 are in `data/daily_status.json` (same fields, every row).

| Jurisdiction | Screen | Date | Price | Address | Why flagged |
|---|---|---|---|---|---|
| DC | assessment ratio (other) | 2026-10-09 | $76,191,000 | 3000 M ST NW WASHINGTON DC 20007-3701 | 2.0x the citywide peer price/assessment ratio, $41,805,760 over assessment |
| DC | assessment ratio (other) | 2026-04-28 | $42,300,000 | TWINING CT NW WASHINGTON DC 20037-1008 | 2.9x the neighborhood peer price/assessment ratio, $27,081,860 over assessment |
| DC | OTR 'Unusual' sale code | 2025-05-06 | $27,000,000 | 2900 M ST NW WASHINGTON DC 20007-3735 | OTR-coded Unusual sale at 1.81x the pre-sale assessment |
| DC | OTR 'Unusual' sale code | 2025-05-09 | $26,000,000 | 1200 5TH ST NW WASHINGTON DC 20001-4841 | OTR-coded Unusual sale at 1.71x the pre-sale assessment |
| Montgomery, MD | non-arms-length, priced above assessment | 2025-02-21 | $22,017,672 | 4824 EDGEMOOR LN, BETHESDA | 10.76x assessment on a non-arms-length transfer |
| DC | assessment ratio (other) | 2026-08-19 | $14,000,000 | 6833 4TH ST NW WASHINGTON DC 20012-1901 | 4.0x the citywide peer price/assessment ratio, $10,774,650 over assessment |
| DC | OTR 'Unusual' sale code | 2026-08-19 | $14,000,000 | 6833 4TH ST NW WASHINGTON DC 20012-1901 | OTR-coded Unusual sale at 4.34x the pre-sale assessment |
| DC | assessment ratio (multifamily) | 2025-07-24 | $11,800,000 | 4559 BENNING RD SE WASHINGTON DC 20019-5169 | 3.5x the citywide peer price/assessment ratio, $8,542,640 over assessment |
| DC | OTR 'Unusual' sale code | 2025-07-24 | $11,800,000 | 4559 BENNING RD SE WASHINGTON DC 20019-5169 | OTR-coded Unusual sale at 3.62x the pre-sale assessment |
| DC | assessment + comps (house) | 2026-09-03 | $11,000,000 | 2930 CHAIN BRIDGE RD NW WASHINGTON DC 20016-3408 | 3.8x the neighborhood peer price/assessment ratio, $8,524,050 over assessment |
| DC | assessment ratio (other) | 2026-07-22 | $11,000,000 | 1700 18TH ST NW WASHINGTON DC 20009-2508 | 3.6x the neighborhood peer price/assessment ratio, $8,099,740 over assessment |
| DC | assessment ratio (condo) | 2025-10-20 | $10,175,000 | 3150 SOUTH ST NW # 3B WASHINGTON DC 20007 | 2.1x the neighborhood peer price/assessment ratio, $5,512,970 over assessment |
| Fairfax, VA | assessor-coded atypical | 2025-07-22 | $8,150,000 | 7805 GROVEMONT DR, MCLEAN 22102 | 2.25x pre-sale assessment, assessor code 'Non-representative price based on comps' |
| DC | assessment ratio (multifamily) | 2026-02-03 | $6,273,852 | 4412 GEORGIA AVE NW WASHINGTON DC 20011-7124 | 2.2x the citywide peer price/assessment ratio, $3,559,672 over assessment |
| DC | OTR 'Unusual' sale code | 2026-05-13 | $6,125,000 | 3307 N ST NW WASHINGTON DC 20007-2808 | OTR-coded Unusual sale at 1.53x the pre-sale assessment |
| DC | comps, high side (house) | 2026-06-25 | $6,050,000 | 2823 Q ST NW WASHINGTON DC 20007-3073 | 1.77x comps' $/sqft, 20 comparables |
| DC | assessment + comps (house) | 2026-01-22 | $5,999,000 | 4849 KEMBLE PL NW WASHINGTON DC 20007-1052 | 2.1x the neighborhood peer price/assessment ratio, $3,450,690 over assessment |
| Montgomery, MD | comps | 2025-05-21 | $5,395,000 | 4709 DORSET AVE, CHEVY CHASE | 1.67x comps' $/sqft, 41 comparables |
| DC | assessment + comps (house) | 2025-09-03 | $5,000,000 | 4414 W ST NW WASHINGTON DC 20007 | 1.7x comps' $/sqft, 12 comparables |
| DC | comps, high side (house) | 2025-09-03 | $5,000,000 | 4414 W ST NW WASHINGTON DC 20007 | 1.7x comps' $/sqft, 12 comparables |
| Montgomery, MD | comps | 2025-07-14 | $4,995,000 | 5613 MCLEAN DR, BETHESDA | 2.1x comps' $/sqft, 35 comparables |
| DC | bought high, resold lower | 2017-06-08 | $4,750,000 | 2425 L ST NW # 700 WASHINGTON DC 20037 | resold 2020-12-30 for $3,050,000, 36% below the 2017-06-08 purchase price |
| Montgomery, MD | comps | 2026-06-25 | $4,600,000 | 7602 GLENBROOK RD, BETHESDA | 2.05x comps' $/sqft, 33 comparables |
| DC | assessment + comps (house) | 2025-12-22 | $4,500,000 | 3003 AUDUBON TER NW WASHINGTON DC 20008 | 1.62x comps' $/sqft, 10 comparables |
| DC | assessment ratio (other) | 2025-06-12 | $4,500,000 | 744 GIRARD ST NW WASHINGTON DC 20001 | 2.0x the citywide peer price/assessment ratio, $2,446,960 over assessment |
| DC | comps, high side (house) | 2025-12-22 | $4,500,000 | 3003 AUDUBON TER NW WASHINGTON DC 20008 | 1.62x comps' $/sqft, 10 comparables |
| DC | bought high, resold lower | 2017-07-10 | $4,400,000 | 1726 HOBAN RD NW WASHINGTON DC 20007 | resold 2018-05-04 for $3,600,000, 18% below the 2017-07-10 purchase price |
| DC | comps, high side (house) | 2025-10-23 | $4,180,000 | 4822 QUEBEC ST NW WASHINGTON DC 20016 | 1.31x comps' $/sqft, 11 comparables |
| DC | OTR 'Unusual' sale code | 2025-04-02 | $4,130,000 | 1919 19TH ST NW WASHINGTON DC 20009 | OTR-coded Unusual sale at 1.48x the pre-sale assessment |
| DC | comps, high side (condo) | 2025-02-10 | $4,000,000 | 45 SUTTON SQUARE SW # 908 WASHINGTON DC 20024-3486 | 1.65x comps' $/sqft, 10 comparables |
| Montgomery, MD | comps | 2026-07-30 | $4,000,000 | 5906 CEDAR PKWY, CHEVY CHASE | 2.12x comps' $/sqft, 80 comparables |
| DC | comps, high side (house) | 2025-09-17 | $3,900,000 | 3137 N ST NW WASHINGTON DC 20007-3420 | 1.86x comps' $/sqft, 37 comparables |
| DC | assessment ratio (multifamily) | 2025-09-29 | $3,895,000 | 1810 I ST NE WASHINGTON DC 20002-4053 | 4.7x the neighborhood peer price/assessment ratio, $3,062,990 over assessment |
| DC | assessment ratio (other) | 2026-02-09 | $3,700,000 | 1337 11TH ST NW WASHINGTON DC 20001 | 3.1x the neighborhood peer price/assessment ratio, $2,566,620 over assessment |
| DC | bought high, resold lower | 2018-05-18 | $3,699,000 | 2660 CONNECTICUT AVE NW # 6D WASHINGTON DC 20008-1 | resold 2021-12-10 for $2,500,000, 32% below the 2018-05-18 purchase price |
| DC | assessment + comps (house) | 2026-09-03 | $3,450,000 | 4631 49TH ST NW WASHINGTON DC 20016-4320 | 2.6x the neighborhood peer price/assessment ratio, $2,303,660 over assessment |
| Prince George's, MD | comps | 2026-01-15 | $3,430,000 | 7610 WOODRUFF CT, LAUREL | 6.86x comps' $/sqft, 118 comparables |
| DC | bought high, resold lower | 2018-06-18 | $3,400,000 | 2660 CONNECTICUT AVE NW # 3A WASHINGTON DC 20008-1 | resold 2021-01-26 for $2,225,000, 35% below the 2018-06-18 purchase price |
| DC | comps, high side (house) | 2025-01-23 | $3,350,000 | 1242 POTOMAC ST NW WASHINGTON DC 20007 | 1.52x comps' $/sqft, 17 comparables |
| Montgomery, MD | comps | 2025-07-30 | $3,306,000 | 9400 FALLS RD, POTOMAC | 1.67x comps' $/sqft, 112 comparables |
| DC | comps, high side (house) | 2025-11-10 | $3,300,000 | 4540 DEXTER ST NW WASHINGTON DC 20007 | 1.64x comps' $/sqft, 10 comparables |
| Fairfax, VA | assessor-coded atypical | 2025-11-05 | $3,300,000 | 1207 TOWLSTON RD, GREAT FALLS 22066 | 1.93x pre-sale assessment, assessor code 'Non-representative price based on comps' |
| DC | comps, high side (house) | 2026-10-08 | $3,250,000 | 622 MASSACHUSETTS AVE NE WASHINGTON DC 20002-6006 | 1.66x comps' $/sqft, 10 comparables |
| DC | comps, high side (house) | 2025-11-05 | $3,250,000 | 6455 BARNABY ST NW WASHINGTON DC 20015 | 1.86x comps' $/sqft, 83 comparables |
| DC | bought high, resold lower | 2015-09-01 | $3,250,000 | 1155 23RD ST NW APT 5E WASHINGTON DC 20037-3305 | resold 2017-05-02 for $2,350,000, 28% below the 2015-09-01 purchase price |
| DC | assessment + comps (house) | 2025-01-22 | $3,225,000 | 622 MASSACHUSETTS AVE NE WASHINGTON DC 20002-6006 | 1.65x comps' $/sqft, 16 comparables |
| DC | comps, high side (house) | 2025-01-22 | $3,225,000 | 622 MASSACHUSETTS AVE NE WASHINGTON DC 20002-6006 | 1.65x comps' $/sqft, 16 comparables |
| DC | comps, high side (house) | 2026-05-08 | $3,150,000 | 4608 KENMORE DR NW WASHINGTON DC 20007 | 1.37x comps' $/sqft, 12 comparables |
| Fairfax, VA | assessor-coded atypical | 2025-01-30 | $2,955,697 | 11329 HENDERSON RD, FAIRFAX STATION 22039 | 2.13x pre-sale assessment, assessor code 'Atypical price - could not be verified' |
| DC | assessment + comps (house) | 2025-01-13 | $2,950,000 | 1519 SWANN ST NW WASHINGTON DC 20009 | 1.88x comps' $/sqft, 16 comparables |
| DC | comps, high side (house) | 2025-01-13 | $2,950,000 | 1519 SWANN ST NW WASHINGTON DC 20009 | 1.88x comps' $/sqft, 16 comparables |
| DC | assessment + comps (house) | 2026-04-15 | $2,925,000 | 1213 O ST NW WASHINGTON DC 20005 | 1.49x comps' $/sqft, 16 comparables |
| DC | comps, high side (house) | 2026-04-15 | $2,925,000 | 1213 O ST NW WASHINGTON DC 20005 | 1.49x comps' $/sqft, 16 comparables |
| DC | comps, high side (house) | 2026-06-24 | $2,900,000 | 610 INDEPENDENCE AVE SE WASHINGTON DC 20003 | 1.72x comps' $/sqft, 22 comparables |
| DC | OTR 'Unusual' sale code | 2026-06-24 | $2,900,000 | 610 INDEPENDENCE AVE SE WASHINGTON DC 20003 | OTR-coded Unusual sale at 1.55x the pre-sale assessment |
| DC | assessment + comps (house) | 2026-07-08 | $2,875,000 | 1308 CORCORAN ST NW WASHINGTON DC 20009 | 2.36x comps' $/sqft, 49 comparables |
| DC | comps, high side (house) | 2026-07-08 | $2,875,000 | 1308 CORCORAN ST NW WASHINGTON DC 20009 | 2.36x comps' $/sqft, 49 comparables |
| DC | assessment + comps (house) | 2025-03-07 | $2,800,000 | 3623 R ST NW WASHINGTON DC 20007 | 1.34x comps' $/sqft, 10 comparables |
| DC | comps, high side (house) | 2025-12-11 | $2,800,000 | 1620 RIGGS PL NW WASHINGTON DC 20009 | 1.57x comps' $/sqft, 22 comparables |
| DC | comps, high side (condo) | 2025-07-30 | $2,800,000 | 601 WHARF ST SW # 602 WASHINGTON DC 20024-3769 | 2.02x comps' $/sqft, 15 comparables |

## Caveats

- **This is an automated-only pass.** `docs/overpriced_sales.md` describes the same screens after a round of manual listing checks, which clear most remaining candidates; this file reflects what the code alone can determine as of this run, so its 'unexplained' count will usually run higher, especially for DC house sales that haven't had a one-time manual listing search recorded yet (see `pipeline/listing_checks.py`).
- **The DC 'comps, low side' screen is known to be noisy.** Per `docs/overpriced_sales.md`, a buyer paying far below comparables is dominated by investors buying distressed or long-held houses; the underlying analysis there narrowed 970 such sales down to 65 worth a listing check using extra filters (condition, not-since-resold) that this automated pass does not apply. Treat 'low side' rows below as lower-priority than 'high side' ones unless and until they get a manual look.
- **Thresholds are judgment calls** (comps $/sqft multiplier, dollar/ratio floors, 8%/year appreciation ceiling, days of comp window) -- see each script's docstring in `pipeline/` for the exact numbers and why they were chosen.
- **Coverage.** Comps screens cover houses (and, in DC, condos); multifamily, commercial, and most multi-property sales aren't comps-screened in any jurisdiction.
- **County raw-data caches.** Arlington and Maryland's raw pulls are cached to disk and reused if present; a CI run starts from a clean checkout (no cache), so it always re-pulls. Running this script repeatedly on a machine with an existing `pipeline/.cache/` will reuse stale county data until that cache is deleted.
- **`pipeline/.cache/comps_screen.json`** is a legacy file from an earlier version of this pipeline; nothing currently regenerates it. `listing_checks.py` reads it only if present, so its absence on a clean checkout changes nothing going forward.

_Generated by `pipeline/run_daily.py`. Raw screen output (with no owner names) stays in `pipeline/.cache/`, which is gitignored and not part of this commit._