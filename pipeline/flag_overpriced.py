"""
Flag sales that sold far above what DC's own assessment would predict.

Input: pipeline/.cache/flag_inputs.json from pull_flag_inputs.py.
Output: pipeline/.cache/flag_overpriced.json, plus a printed report of every
count, so nothing is dropped silently.

"Expected" = the published assessment valued BEFORE the sale:
  - sale in 2025 -> OLDTOTAL (tax year 2026, valued as of 2025-01-01)
  - sale in 2026 -> NEWTOTAL (tax year 2027, valued as of 2026-01-01)
(pull_flag_inputs.py checks CY1YEAR = 2026 for this mapping; this script
refuses to run if any ITSPE row says otherwise.)

Multi-property deals. Every SALE_CODE starting with "M" is a deal covering
several properties, and the WHOLE deal price is recorded on each property's
row. Measured on the 2026-11-21 pull: 99.9%-100% of M-coded rows share their
exact (date, price) with another row (median deal: 3 properties), against 2.6%-
10% for plain codes. Comparing that price with ONE property's assessment made
70% of M1 rows look 5x+ "overpriced". So M-coded rows are grouped into one deal
per (SALE_DATE, SALE_PRICE) and the deal price is compared with the SUM of the
assessments of every property in the deal. (Codes are not defined in the
layer's metadata or in OTR's appraisal manuals we checked; the grouping rests on
the measured pattern above.)

The flag: a transaction is flagged when its price-to-assessment ratio is at
least RATIO_MULT times the median ratio of comparable QUALIFIED ('Q') sales in
the same assessment neighborhood and property class (falling back to the
citywide class median when the neighborhood has fewer than MIN_PEERS qualified
sales), AND the price exceeds the assessment by at least MIN_DOLLARS. The
neighborhood median absorbs areas where assessments lag the market everywhere;
the dollar floor keeps $30K parking spaces from dominating.

The flag says a price was far above the assessment. It does not say why:
renovation after the valuation date, a stale assessment, a bundled business or
personal property, or a data error all produce the same ratio. Buyer and seller
names are not used anywhere.
"""
from __future__ import annotations

import json
import os
import statistics
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
INP = os.path.join(HERE, ".cache", "flag_inputs.json")
OUT = os.path.join(HERE, ".cache", "flag_overpriced.json")

RATIO_MULT = 2.0       # flagged if ratio >= 2x the peer median ratio
MIN_DOLLARS = 100_000  # ... and price - assessment >= $100K
MIN_PEERS = 20         # qualified sales needed for a neighborhood-level median


USECODES = os.path.join(HERE, ".cache", "usecodes.json")


def prop_class(usecode: str, desc: dict) -> str:
    """Class from the DESCRIPTION in DC's USECODE lookup (layer 54, cached to
    .cache/usecodes.json), not from the code's leading digit. The first version
    guessed 0xx = residential, 2xx = condo; that put condo PARKING spaces (018
    Residential-Condo-Garage) with houses and gave 'condo' a nonsense median
    ratio of 1.71."""
    t = (desc.get((usecode or "").strip()) or "").lower()
    if "garage" in t or "parking" in t:
        return "parking"
    if "vacant" in t:
        return "vacant"
    if "condo" in t and "commercial" not in t and "retail" not in t and "office" not in t:
        return "condo"
    if "single-family" in t:
        return "house"
    if any(k in t for k in ("apartment", "conversion", "flats", "multi")):
        return "multifamily"
    return "other"


def deal_class(classes: set) -> str:
    """One class per transaction. Multi-property deals are mostly bundles: on the
    2026-11-21 pull, 986 of 1,200 mixed deals were a condo unit plus its parking
    space and 110 a house plus an adjoining lot. So parking and vacant parcels
    are ignored when one main class remains; otherwise 'mixed', which is
    compared with the citywide median of all qualified sales."""
    if len(classes) == 1:
        return next(iter(classes))
    main = classes - {"parking", "vacant"}
    if len(main) == 1:
        return next(iter(main))
    if not main:
        return "vacant" if "vacant" in classes else "parking"
    return "mixed"


def main():
    with open(INP) as fh:
        d = json.load(fh)
    itspe = {r["SSL"]: r for r in d["itspe"]}
    with open(USECODES) as fh:
        desc = json.load(fh)
    # Year BUILT (AYB) per SSL from residential CAMA, newest building on the lot.
    # Only AYB sets a sale aside. YR_RMDL / EYB are the CAMA record's CURRENT
    # values and can be updated after a sale: the 2026-06-24 Capitol Hill sale
    # that motivated this flag shows YR_RMDL 2026 though press reporting found no
    # permits or work between the valuation date and the sale. Using YR_RMDL
    # would hide exactly the cases this flag exists to surface, so it is only
    # reported (remodel_year_in_cama), never used to exclude.
    built, remodel = defaultdict(int), defaultdict(int)
    for c in d["res_cama"]:
        built[c["SSL"]] = max(built[c["SSL"]], int(c.get("AYB") or 0))
        remodel[c["SSL"]] = max(remodel[c["SSL"]], int(c.get("YR_RMDL") or 0))
    years = Counter(r.get("CY1YEAR") for r in d["itspe"])
    if set(years) != {"2026"}:
        raise SystemExit(f"CY1YEAR is {dict(years)}; the OLDTOTAL/NEWTOTAL mapping assumes 2026. Re-check before running.")

    report = {"pulled_at": d["pulled_at"], "sales_rows": len(d["sales"])}

    # 1. Build transactions.
    deals = defaultdict(list)
    singles = []
    for s in d["sales"]:
        if (s.get("SALE_CODE") or "").startswith("M"):
            deals[(s["SALE_DATE"], s["SALE_PRICE"])].append(s)
        else:
            singles.append([s])
    txns = singles + list(deals.values())
    report["transactions"] = {"single_property": len(singles), "multi_property_deals": len(deals),
                              "multi_property_rows": sum(len(v) for v in deals.values()),
                              "multi_property_deals_with_one_row": sum(1 for v in deals.values() if len(v) == 1)}

    # 2. Expected value = summed pre-sale assessment.
    rows, dropped = [], Counter()
    for t in txns:
        first = t[0]
        price = first["SALE_PRICE"]
        col = "OLDTOTAL" if first["SALE_DATE"] < "2026-01-01" else "NEWTOTAL"
        props = [itspe.get(s["SSL"]) for s in t]
        if any(p is None for p in props):
            dropped["no ITSPE row"] += 1
            continue
        assessed = sum((p.get(col) or 0) for p in props)
        if assessed <= 0:
            dropped["total assessment $0"] += 1
            continue
        classes = {prop_class(p.get("USECODE"), desc) for p in props}
        val_year = 2025 if col == "OLDTOTAL" else 2026
        later = sum((p.get("NEWTOTAL") or 0) for p in props) if col == "OLDTOTAL" else None
        nbhds = {p.get("NBHD") for p in props}
        rows.append({
            "ssls": [s["SSL"] for s in t], "n_properties": len(t), "sale_date": first["SALE_DATE"],
            "price": price, "assessment_col": col, "assessed": assessed, "ratio": price / assessed,
            "qualified": "Q" if all(s["QUALIFIED"] == "Q" for s in t) else "U",
            "sale_codes": sorted({s["SALE_CODE"] for s in t}),
            "class": deal_class(classes),
            "nbhd": nbhds.pop() if len(nbhds) == 1 else None,
            "nbhd_name": props[0].get("NBHDNAME") if len({p.get("NBHD") for p in props}) == 1 else "multiple",
            "address": props[0].get("PREMISEADD"),
            "valued_as_of": f"{val_year}-01-01",
            "year_built": max(built.get(s["SSL"], 0) for s in t) or None,
            "remodel_year_in_cama": max(remodel.get(s["SSL"], 0) for s in t) or None,
            "later_assessment": later,
        })
    report["dropped"] = dict(dropped)

    # 3. Peer medians from qualified single-property sales.
    peers_n, peers_c = defaultdict(list), defaultdict(list)
    for r in rows:
        if r["qualified"] == "Q" and r["n_properties"] == 1:
            peers_n[(r["nbhd"], r["class"])].append(r["ratio"])
            peers_c[r["class"]].append(r["ratio"])
    med_n = {k: statistics.median(v) for k, v in peers_n.items() if len(v) >= MIN_PEERS}
    med_c = {k: statistics.median(v) for k, v in peers_c.items()}
    med_c["mixed"] = statistics.median([x for v in peers_c.values() for x in v])
    report["citywide_class_median_ratio"] = {k: round(v, 3) for k, v in med_c.items()}

    flagged, near, no_peer, set_aside = [], [], 0, []
    for r in rows:
        key = (r["nbhd"], r["class"])
        if key in med_n:
            r["peer_median"], r["peer_level"] = med_n[key], "neighborhood"
        elif r["class"] in med_c:
            r["peer_median"], r["peer_level"] = med_c[r["class"]], "citywide"
        else:
            no_peer += 1
            continue
        r["ratio_vs_peers"] = r["ratio"] / r["peer_median"]
        over = r["price"] - r["assessed"]
        if r["ratio_vs_peers"] >= RATIO_MULT and over >= MIN_DOLLARS:
            # Set aside, with the reason, cases where the gap has an ordinary
            # explanation the data can see. Counted in the report, kept in output.
            vy = int(r["valued_as_of"][:4])
            if any(c.startswith("M") for c in r["sale_codes"]) and r["n_properties"] == 1:
                r["set_aside"] = "multi-property code but only one property found (the price likely covers parcels not matched)"
            elif r["class"] == "vacant":
                r["set_aside"] = "vacant land (price likely reflects planned or ongoing construction)"
            elif (r["year_built"] or 0) >= vy:
                r["set_aside"] = f"built {r['year_built']}, on/after the {vy}-01-01 valuation"
            elif r["later_assessment"] and r["price"] / r["later_assessment"] < RATIO_MULT * r["peer_median"]:
                r["set_aside"] = "the next assessment (valued 2026-01-01) is within range of the price"
            if r.get("set_aside"):
                set_aside.append(r)
            else:
                flagged.append(r)
        elif r["ratio_vs_peers"] >= RATIO_MULT * 0.9 or (r["ratio_vs_peers"] >= RATIO_MULT and over >= MIN_DOLLARS * 0.5):
            near.append(r)
    report["no_peer_median"] = no_peer
    report["peer_level"] = dict(Counter(r.get("peer_level", "none") for r in rows))
    report["flagged"] = len(flagged)
    report["flagged_by_code"] = dict(Counter(c for r in flagged for c in r["sale_codes"]))
    report["flagged_by_class"] = dict(Counter(r["class"] for r in flagged))
    report["flagged_by_qualified"] = dict(Counter(r["qualified"] for r in flagged))
    report["near_threshold"] = len(near)
    report["set_aside"] = dict(Counter(("built on/after valuation" if r["set_aside"].startswith("built") else r["set_aside"].split(" (")[0]) for r in set_aside))

    flagged.sort(key=lambda r: -r["ratio_vs_peers"])
    with open(OUT, "w") as fh:
        json.dump({"params": {"RATIO_MULT": RATIO_MULT, "MIN_DOLLARS": MIN_DOLLARS, "MIN_PEERS": MIN_PEERS},
                   "report": report, "flagged": flagged, "set_aside": set_aside, "near_threshold": near}, fh, indent=1)
    print(json.dumps(report, indent=1))
    print(f"\nTop 15 flagged (of {len(flagged)}):")
    for r in flagged[:15]:
        print(f"  {r['sale_date']}  ${r['price']:>12,.0f} vs ${r['assessed']:>11,.0f}  x{r['ratio']:.1f} ({r['ratio_vs_peers']:.1f}x peers, {r['peer_level']})  "
              f"{r['class']:11} {r['qualified']} {','.join(r['sale_codes'])}  n={r['n_properties']}  {r['address']}  [{r['nbhd_name']}]")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
