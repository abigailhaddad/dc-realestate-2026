# Finding home sales that sold far above anything comparable

This documents a screen for residential sales whose price is far out of line
with comparable sales, built from public property records in DC, Arlington,
Montgomery and Prince George's counties (MD), and Fairfax County (VA). It was
prompted by a 2026 press report of an off-market Capitol Hill sale that closed
well above the price at which the same house had failed to sell months earlier.

**It flags transactions, not people.** No buyer or seller names are used in any
screen, and the per-property results are kept out of this repository
(`pipeline/.cache/`, gitignored). A flagged sale is a reason to look, not a
finding: almost every flag here turned out to have an ordinary explanation.

## The short version

Across about 59,000 sales from January 2025 to November 2026 (house sales in
DC, Arlington and Maryland; all sales in Fairfax), the screens surfaced about
500 sales that looked far above their neighborhood.
After automatic checks against each property's own records and a listing check
on what remained, **almost all were ordinary**. The ordinary causes, in rough
order of frequency:

1. **Stale county records.** County house sizes and year-built fields often
   lag renovations, additions and rebuilds. A listing showed a 5-bedroom,
   4.5-bath house where the state record said 1,040 sq ft. These houses look
   overpriced per square foot only because the county still has the old house.
2. **Steady appreciation.** The property's own earlier sale, compounded at a
   normal rate (8%/year or less), explains the price.
3. **Renovation flips and teardowns.** A construction, addition or demolition
   permit between the purchase and the resale, or a buyer paying for the land.
4. **Large lots and farms.** Comparing house size ignores land; farmland is
   assessed at agricultural use value.
5. **Ordinary bidding.** The house was publicly listed and sold at or near its
   asking price, or in a documented bidding war.
6. **Data-entry errors.** One state record showed $3,430,000 for a sale the
   listing records put at $343,000.

What stays open is a short list of sales with **no public listing found** and
no explanation in the public record, plus the case that prompted the work.

## Data sources (all public, no API keys)

| Jurisdiction | Source | Sales through | Notes |
|---|---|---|---|
| DC | Office of Tax and Revenue on `maps2.dcgis.dc.gov` (sales, ITSPE, residential CAMA); DOB building permits 2009-2026 (FEEDS/DCRA) | 2026-11 | `pull_flag_inputs.py` |
| Arlington, VA | County real-estate DataHub `datahub-v2.arlingtonva.us/api/RealEstate/*`; permits `/api/Permit/Permit` | 2026-11-18 | `counties/arlington.py` |
| Montgomery & Prince George's, MD | State assessment file, opendata.maryland.gov dataset `ed4q-f8tm` (SDAT/MDP); county permits (Montgomery `m88u-pqki`, Prince George's `weik-ttee`) | 2026-10-29 | `counties/maryland.py` |
| Fairfax, VA | Department of Tax Administration tables on the county's ArcGIS open-data services (sales, assessed values, dwelling, parcel, legal) | 2026-09-15 | `counties/fairfax.py` |

### Field quirks found and handled

- **DC.** Every sale code starting with `M` is a multi-property deal with the
  whole price recorded on each property (99.9-100% of `M` rows share their exact
  date and price with another row); these are grouped and compared with the
  summed assessment. `SALE_CURR_OWNER` is a `"1"`/`"0"` string flag, not a name.
  The residential remodel year (`YR_RMDL`) can be updated after a sale, so it is
  never used to excuse one; year built (`AYB`) and permits are.
- **Arlington.** The API's `$skip` paging is unstable without a sort order.
  The first pull silently returned duplicate rows in place of about 21% of the
  sales history (242,000 unique of 309,000) and missed 332 of the 4,079
  properties sold since 2025; it is now sorted on every selected field. (An
  earlier draft blamed the county feed for "73,000 duplicate rows"; that was
  our bug. The feed itself repeats about 4,200 rows.) House area is not `grossFloorAreaSquareFeetQty` (blank for
  houses); it is summed from the interior table. The county's own sale codes
  include `P` ("Not listed MLS/online"), a direct off-market flag, and `G` (new
  construction).
- **Maryland.** The mortgage field has not been populated since about 2023, so
  nothing here says a purchase was all-cash. There is no assessment-neighborhood
  field, so comparables group by ZIP. Land area mixes acres and square feet.
  Some transfer dates are impossible (a 2031 date) and at least two prices
  disagree with listing records.
- **Fairfax.** The assessor codes every sale's validity after review, including
  "Non-representative price based on comps" and "Atypical price - could not be
  verified". The Fairfax screen uses those codes instead of its own comparables.

## Method

1. **Comparables screen (DC, Arlington, Maryland).** For each house sale,
   take qualified sales in the same neighborhood (DC assessment neighborhood;
   Arlington 4-digit neighborhood code; Maryland ZIP and residence type) within
   six months (Arlington: a year), with living area within 25% and (where
   available) bedrooms within one. A sale is a candidate when at most one
   comparable sold at or above its price and its price per square foot is at
   least 1.3x the comparables' median. At least 10 comparables are required
   (Arlington: 8).
   **Fairfax** instead takes sales the assessor coded atypical and priced at
   least 1.5x the pre-sale assessment.
2. **Automatic explanations**, each counted and kept in the output with its
   reason:
   - new construction (year built in or just before the sale year), or the
     house rebuilt since its previous sale;
   - consistent with its own sale history (previous sale at least a year
     earlier, at most 8%/year growth since);
   - construction, addition, alteration or demolition permit from two years
     before to one year after the sale;
   - farm (agricultural use assessment) or lot of 2 acres or more;
   - sale price within 1.3x the county's own assessment (Maryland);
   - the county's own codes (Arlington new construction; Fairfax remodel year).
3. **Listing check (by hand, one web search per sale).** Was the house publicly
   listed, and how did the sale price compare with the last asking price?
   Verdicts: *cleared* (listed, sold at or below asking), *normal bidding* (up
   to 10% over), *keep* (no listing found, delisted and then sold above the last
   asking price, or more than 10% over). Zillow, Redfin and the MLS forbid
   scraping, and DC's Recorder of Deeds site disallows automated access, so this
   step is manual; results are recorded with source URLs.

## Results by jurisdiction

| | DC | Arlington | Montgomery + PG | Fairfax |
|---|---|---|---|---|
| House sales screened | 5,285 with 10+ comparables | 1,715 with 8+ comparables | 24,142 with 10+ comparables | 1,578 assessor-coded atypical (of 25,676 sales) |
| Candidates | 100 (plus 29 from a stricter first screen and 7 assessment-flag houses) | 56, plus 15 assessor-coded "not a market sale" (N) at 1.3x+ assessment | 361 | 18 (one vacant land, set aside) |
| Explained automatically | 24 by own sale history; 42 dropped up front for construction permits | 54 of the comparables candidates; 12 of the N sales | 284 | 9 (+1 found on a second search: an institutional buyer for a care facility) |
| Listing-checked | 57 (9 then explained by permits) | 8 (3 comparables, 2 county-coded off-market, 3 N) | 51 | 8 |
| Cleared or normal bidding | 43 | 3 (+3 a builder's land price or a low assessment) | 42 (+2 bidding wars) | 4 (incl. 2 bidding/flip) |
| Data errors found | 0 | 0 | 2 | 0 |
| Explained on a second search | 1 (rebuild) | 0 | 1 (bought off-market, relisted 31% higher two months later) | 0 |
| Still open (after a second round of searches, 2026-11-21) | 2: the press-report case, and one sold 10.1% over asking | 2, low priority | 2, low priority (small houses on large lots) | 2: one with no listing anywhere, one McLean acreage sale that's plausibly market |

"Still open" means no explanation was found in public records. For nearly all
of these the only unusual fact is that no public listing turned up, which can
also mean the sale was off-MLS for ordinary reasons (a sale to a neighbor, a
builder, or a relative not coded as such).

One DC sale stands out from everything else: the case in the press report,
which was delisted after failing to sell and then sold off-market 46% above its
last asking price. A second DC sale that looked similar (about four times its
price from 21 months earlier, no construction permit in DC's open data, no
listing found at first) turned out on a closer search to be a broker-listed sale
of a house rebuilt to roughly four times its former size. **DC's open permit
data missed that rebuild entirely**, so "no permit found" is weak evidence.

## Other shapes a favor can take (DC, `patterns.py`)

The screens above were built around one case. A favor through real estate is
value moving between buyer and seller at a price the market wouldn't set, and
the next one may look different. Four more DC screens, run 2026-11-21 on OTR
sales from 2015 (163,284 rows) and citywide parcel data:

| Screen | What it looks for | Result |
|---|---|---|
| **OTR "Unusual" code** | 2025+ sales the tax office itself coded 04 "Unusual", priced at least 1.3x the pre-sale assessment | 50 sales; 24 explained (new construction, permits); 26 left, of which 9 are houses or condos. The press-report sale is one. Listing checks on the other 8: 4 publicly listed and sold at or below asking, 4 no listing found. **The best new screen**: short, and it uses the tax office's own review. Not proof alone. |
| **Far below comparables** | The discount case: a buyer paying far less than comparable sales (houses and condos) | 970 sales, dominated by investors buying distressed or long-held houses (OTR codes 07 "Speculative" and 04). Narrowed to market or unusual sales at 70% or less of assessment, a discount of $150K or more, condition not poor, not since resold: 65. **Too noisy to use without listing checks**; estate and as-is sales look identical in this data. |
| **Bought high, resold low** | A buyer who later resold, in an ordinary market sale, at a 15%+ nominal loss and far below the market for the same years | 83; 15 explained as bought new. The remaining 68 are mostly condos. Too few same-building resales exist to rule out a building-wide decline. **Weak in DC.** A first version compared against all market resales; short-hold resales are dominated by renovation flips, which made flat resales look like large losses, so the baseline now uses holds of 2+ years only. |
| **Condos, comparables above** | The original high-side test applied to condos | 115 candidates, not yet listing-checked |

Two descriptors are now attached to every candidate whose sale is the current
owner's purchase. They describe the holding, never the holder:
- **homestead deduction claimed now** (`HSTDCODE`);
- **tax-escrow servicer on file now** (`MORTGAGECO` reduced to yes/no). Yes means a mortgage with escrow; no means cash or a loan without escrow.

The press-report sale has neither. These are descriptors, not filters: most
buyers without a homestead claim are landlords or second-home owners, and
escrow is optional on many loans.

**Starting from officials instead doesn't reach this kind of sale.** The House
Ethics Committee's 2025 disclosure instructions tell members not to disclose a
personal residence, or its purchase or sale, unless it earned rental income
(Schedule A and Schedule B exclusions). Members do disclose mortgages on a
personal residence, but only by city. A residence sale like the one that
prompted this work would not appear in a member's disclosure.

**Assessments jump after a sale.** For tax year 2027 (valued 2026-01-01), DC
houses that sold in 2025 rose a median 4.3%, against 1.5% for houses that didn't
sell (Georgetown: 11.6% against 4.1%). In Georgetown, 31 of 127 sold houses rose
25% or more, against 49 of 2,252 unsold. Part of this may be renovation records
updated around a sale. Either way, an assessment set after a sale partly
reflects that sale's price, so it can't be used to check whether the price was
fair. Every screen here uses the assessment from before the sale.

## Limits

- **Coverage.** Only house sales (single-family, rowhouse, townhouse) are
  screened by comparables; condos, multifamily and commercial sales are not.
- **Listing history is the decisive check and it is manual.** It depends on
  what listing aggregators index; recent sales may not appear yet.
- **County records lag.** Sizes, year built and remodel fields are often out of
  date, which is the largest single source of false flags.
- **Permit data is incomplete.** DC's open permit layers lacked the main
  construction permit for a house rebuilt to four times its size; absence of a
  permit is not evidence that no work was done.
- **No ownership analysis.** Buyer identity, deed details and financing are not
  part of the screen. They are in deed records, which are searched by hand.
- **Thresholds are judgment calls** (1.3x price per square foot, 8%/year, 1.5x
  assessment, 10% over asking). Items near each cutoff were listed when the
  screens ran.

## Rerunning

```bash
cd pipeline
python3 pull_flag_inputs.py         # DC inputs
python3 flag_overpriced.py          # DC assessment-ratio flag
python3 screen_candidates.py        # DC comparables screen + permit filter
python3 history_check.py            # DC own-sale-history check
python3 listing_checks.py todo      # what still needs a listing search
python3 listing_checks.py classify  # verdicts -> .cache/shortlist.json
python3 pull_history.py           # DC sales 2015+ (for the resale screen)
python3 pull_parcels.py           # DC citywide parcels, house + condo sizes
python3 patterns.py               # DC: Unusual code, below comps, resold lower, condos
python3 counties/arlington.py
python3 counties/maryland.py
python3 counties/fairfax.py
```

All outputs go to `pipeline/.cache/` (gitignored).
