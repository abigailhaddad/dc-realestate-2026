"""
Montgomery and Prince George's counties, MD: the "sold far above anything
comparable" screen, from the state's public assessment file.

Source: Maryland SDAT/MDP "Maryland Real Property Assessments" on
opendata.maryland.gov, dataset ed4q-f8tm (Socrata, no key). Rows refreshed
2026-11-06; latest transfer date in these two counties 2026-10-29 when read
(2026-11-21). One row per property with its LAST THREE transfers.

Read before changing (checked 2026-11-21):
  - County names are 'Montgomery' and "Prince George's" (no "County").
  - How-conveyed codes: (1) arms-length improved, (2) arms-length vacant,
    (3) arms-length multiple parcel, (4) non-arms-length (foreclosure, gift,
    auction). Only (1) is screened; (3) is reported, (4) dropped and counted.
  - The MORTGAGE field is not populated for recent sales (0 of 31,940 arms-length
    2025-26 sales above 0; Montgomery had 663 in 2019, 109 in 2021, 0 in 2023), so
    it is not used and nothing here says a sale was all-cash.
  - There is no assessment-neighborhood field; comps group by premise ZIP and
    residence type (SF / TH / CN).
  - Some transfer dates are impossible (max seen 2031.01.11); only 2025-01-01..
    2026-12-31 is read.
  - Grantor (seller) names exist in this file and are never requested.

Assessment used: current-cycle land + improvements (full market value at the
property's last triennial reassessment, date in 'assessed').

    python3 counties/maryland.py  -> .cache/maryland/screen.json + table
"""
from __future__ import annotations

import json
import os
import statistics
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.dirname(HERE), ".cache", "maryland")
URL = "https://opendata.maryland.gov/resource/ed4q-f8tm.json"
F = {
    "county": "county_name_mdp_field_cntyname",
    "acct": "account_id_mdp_field_acctid",
    "addr": "mdp_street_address_mdp_field_address",
    "city": "mdp_street_address_city_mdp_field_city",
    "zip": "premise_address_zip_code_mdp_field_premzip_sdat_field_26",
    "restype": "mdp_street_address_type_code_mdp_field_resityp",
    "landuse": "land_use_code_mdp_field_lu_desclu_sdat_field_50",
    "sqft": "c_a_m_a_system_data_structure_area_sq_ft_mdp_field_sqftstrc_sdat_field_241",
    "yrblt": "c_a_m_a_system_data_year_built_yyyy_mdp_field_yearblt_sdat_field_235",
    "grade": "c_a_m_a_system_data_dwelling_grade_code_and_description_mdp_field_strugrad_strudesc_sdat_field_230",
    "landarea": "c_a_m_a_system_data_land_area_mdp_field_landarea_sdat_field_242",
    "luom": "c_a_m_a_system_data_land_unit_of_measure_mdp_field_luom_sdat_field_243",
    "prefland": "current_cycle_data_preferential_land_value_sdat_field_166",
    "premnum": "premise_address_number_mdp_field_premsnum_sdat_field_20",
    "premname": "premise_address_name_mdp_field_premsnam_sdat_field_23",
    "land": "current_cycle_data_land_value_mdp_field_names_nfmlndvl_curlndvl_and_sallndvl_sdat_field_164",
    "impr": "current_cycle_data_improvements_value_mdp_field_names_nfmimpvl_curimpvl_and_salimpvl_sdat_field_165",
    "assessed": "current_cycle_data_date_assessed_yyyy_mm_mdp_field_lastassd_sdat_field_169",
    "d1": "sales_segment_1_transfer_date_yyyy_mm_dd_mdp_field_tradate_sdat_field_89",
    "p1": "sales_segment_1_consideration_mdp_field_considr1_sdat_field_90",
    "c1": "sales_segment_1_how_conveyed_ind_mdp_field_convey1_sdat_field_87",
    "d2": "sales_segment_2_transfer_date_yyyy_mm_dd_sdat_field_109",
    "p2": "sales_segment_2_consideration_sdat_field_110",
    "c2": "sales_segment_2_how_conveyed_ind_sdat_field_107",
    "d3": "sales_segment_3_transfer_date_yyyy_mm_dd_sdat_field_129",
    "p3": "sales_segment_3_consideration_sdat_field_130",
    "c3": "sales_segment_3_how_conveyed_ind_sdat_field_127",
}
MIN_COMPS, MAX_HIGHER, PPSF_MULT, WINDOW = 10, 1, 1.3, 183
MIN_YEARS, MAX_CAGR = 1.0, 0.08
NONARM_RATIO = 1.3


def fetch():
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "rows.json")
    if os.path.exists(p):
        return json.load(open(p))
    where = (f"{F['county']} in ('Montgomery','Prince George''s') AND {F['d1']} >= '2025.01.01' "
             f"AND {F['d1']} <= '2026.12.31'")
    rows, off = [], 0
    while True:
        q = urllib.parse.urlencode({"$select": ",".join(F.values()), "$where": where, "$limit": 50000,
                                    "$offset": off, "$order": F["acct"]})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(f"{URL}?{q}", headers={"User-Agent": "dc-realestate-pipeline"}), timeout=300) as r:
                    page = json.load(r)
                break
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(10)
        if isinstance(page, dict):
            raise RuntimeError(page)
        rows += page
        if len(page) < 50000:
            break
        off += 50000
    json.dump(rows, open(p, "w"))
    return rows


def _soql(url, where, select):
    q = urllib.parse.urlencode({"$where": where, "$select": select, "$limit": 200})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{url}?{q}", headers={"User-Agent": "dc-realestate-pipeline"}), timeout=120) as r:
                d = json.load(r)
            if isinstance(d, dict):
                raise RuntimeError(d)
            return d
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5)


def permits(r):
    """Construction-type permits at the sale's address, sale-730d .. sale+365d."""
    from datetime import timedelta
    d0 = date.fromisoformat(r["date"])
    lo, hi = (d0 - timedelta(days=730)).isoformat(), (d0 + timedelta(days=365)).isoformat()
    num_, word = r["premnum"], (r["premname"].split() or [""])[0].replace("'", "''")
    if not num_ or not word:
        return []
    out = []
    if r["county"] == "Montgomery":
        rows = _soql("https://data.montgomerycountymd.gov/resource/m88u-pqki.json",
                     f"stno='{num_}' AND upper(stname) like '{word}%' AND zip='{r['zip']}' "
                     f"AND issueddate >= '{lo}' AND issueddate <= '{hi}'",
                     "issueddate,worktype,usecode,description,applicationtype")
        for x in rows:
            wt = (x.get("worktype") or "").upper()
            if any(k in wt for k in ("CONSTRUCT", "ADD", "ALTER", "DEMOL", "RAZE", "BUILD", "REPLACE")) and \
                    (x.get("usecode") or "").upper() not in ("SHED", "FENCE", "DECK", "POOL", "RETAINING WALL"):
                out.append((x["issueddate"][:10], f"{wt} {x.get('usecode') or ''} - {(x.get('description') or '')[:80]}"))
    else:
        rows = _soql("https://data.princegeorgescountymd.gov/resource/weik-ttee.json",
                     f"upper(street_address) like '{num_} {word}%' AND zip_code='{r['zip']}' "
                     f"AND permit_issuance_date >= '{lo}' AND permit_issuance_date <= '{hi}'",
                     "permit_issuance_date,permit_type,case_name,expected_construction_cost")
        for x in rows:
            pt = (x.get("permit_type") or "").upper()
            if any(k in pt for k in ("BUILDING", "ALTERATION", "ADDITION", "RAZE", "DEMOL", "NEW", "RENOV")):
                out.append((x["permit_issuance_date"][:10], f"{pt} - {(x.get('case_name') or '')[:80]}"))
    return sorted(out)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def iso(d):
    return d.replace(".", "-") if d and len(d) == 10 else None


def explain(rs):
    """Ordinary explanations, recorded per row (shared by both screens)."""
    for r in rs:
        prior = [p for p in r["prior"] if p[0] < r["date"] and p[1] > 0 and "(4)" not in p[2]]
        if prior:
            pd, pp, _ = max(prior)
            yrs = (date.fromisoformat(r["date"]) - date.fromisoformat(pd)).days / 365.25
            cagr = (r["price"] / pp) ** (1 / yrs) - 1 if yrs > 0 else None
            r.update(prev_date=pd, prev_price=pp, cagr=round(cagr, 4) if cagr is not None else None)
            hist_ok = yrs >= MIN_YEARS and cagr is not None and cagr <= MAX_CAGR
        else:
            hist_ok = False
        new_build = (r["yrblt"] or 0) >= int(r["date"][:4]) - 1
        rebuilt = bool(r.get("prev_date")) and (r["yrblt"] or 0) > int(r["prev_date"][:4])
        r["explained"] = ("new construction (year built %s)" % r["yrblt"] if new_build else
                          "rebuilt since previous sale (built %s, last sold %s)" % (r["yrblt"], r["prev_date"][:4]) if rebuilt else
                          "consistent with own sale history" if hist_ok else None)

    # 2026-11-21 cleanup of what the comps + history rules leave:
    #   farm: preferential (agricultural-use) land value > 0 or land use Agricultural;
    #         price vs a use-value assessment means nothing.
    #   large lot: >= 2 acres; comps by house size don't capture land.
    #   permits: construction / alteration / demolition permit at the address from
    #         730 days before to 365 days after the sale (renovation, or a buyer
    #         paying for land to rebuild). Montgomery DPS m88u-pqki, PG DPIE weik-ttee,
    #         matched by street number + first word of street name + ZIP.
    for r in rs:
        if r["explained"]:
            continue
        acres = r["landarea"] if r["luom"] == "A" else r["landarea"] / 43560.0
        if r["prefland"] > 0 or "Agricultur" in r["landuse"]:
            r["explained"] = "farm (agricultural use assessment)"
        elif acres >= 2:
            r["explained"] = f"large lot ({acres:.1f} acres); house-size comps don't apply"
    todo = [r for r in rs if not r["explained"]]
    for r in todo:
        pm = permits(r)
        r["permits_window"] = pm
        if pm:
            when = "after" if all(x[0] > r["date"] for x in pm) else "before/around"
            r["explained"] = f"construction/alteration/demolition permit {when} the sale ({pm[0][0]}: {pm[0][1]})"


def main():
    raw = fetch()
    R = {k: [] for k in ("rows",)}
    rows = []
    for x in raw:
        g = {k: x.get(v) for k, v in F.items()}
        d = iso(g["d1"])
        if not d:
            continue
        rows.append({"acct": g["acct"], "county": g["county"], "date": d, "price": num(g["p1"]), "conv": g["c1"] or "",
                     "zip": (g["zip"] or "")[:5], "restype": g["restype"], "sqft": num(g["sqft"]),
                     "yrblt": int(num(g["yrblt"])) or None, "landarea": num(g["landarea"]),
                     "luom": (g["luom"] or "").strip().upper()[:1], "prefland": num(g["prefland"]), "landuse": g["landuse"] or "",
                     "premnum": (g["premnum"] or "").strip().lstrip("0"), "premname": (g["premname"] or "").strip().upper(), "grade": g["grade"], "assessed": num(g["land"]) + num(g["impr"]),
                     "assessed_as_of": g["assessed"], "address": f"{g['addr'] or ''}, {g['city'] or ''}",
                     "prior": [(iso(g[f"d{i}"]), num(g[f"p{i}"]), g[f"c{i}"] or "") for i in (2, 3) if iso(g[f"d{i}"])]})
    conv = Counter(r["conv"] for r in rows)
    arms = [r for r in rows if "(1)" in r["conv"] and r["price"] > 0]
    house = [r for r in arms if r["restype"] in ("SF", "TH") and r["sqft"] > 0]
    report = {"rows_with_2025_26_transfer": len(rows), "latest_transfer": max(r["date"] for r in rows),
              "by_conveyance": dict(conv), "arms_length_improved_price_gt0": len(arms),
              "houses_with_size": len(house)}

    pool = defaultdict(list)
    for r in house:
        pool[(r["county"], r["zip"], r["restype"])].append(r)
    cands, n_eval = [], 0
    for r in house:
        d0 = date.fromisoformat(r["date"])
        comps = [c for c in pool[(r["county"], r["zip"], r["restype"])] if c["acct"] != r["acct"]
                 and abs((date.fromisoformat(c["date"]) - d0).days) <= WINDOW
                 and abs(c["sqft"] - r["sqft"]) <= 0.25 * r["sqft"]]
        if len(comps) < MIN_COMPS:
            continue
        n_eval += 1
        r["n_comps"] = len(comps)
        r["n_higher"] = sum(c["price"] >= r["price"] for c in comps)
        r["comps_median"] = statistics.median(c["price"] for c in comps)
        r["ppsf_mult"] = round((r["price"] / r["sqft"]) / statistics.median(c["price"] / c["sqft"] for c in comps), 2)
        r["ratio"] = round(r["price"] / r["assessed"], 2) if r["assessed"] else None
        if r["n_higher"] <= MAX_HIGHER and r["ppsf_mult"] >= PPSF_MULT:
            cands.append(r)

    explain(cands)

    # Non-arms-length (how-conveyed 4) transfers priced far above assessment.
    # Why (2026-11-21): DC's tax office coded the press-report sale "Unusual";
    # the state file's nearest equivalent is code (4), which the comps screen
    # drops. Non-arms-length transfers (gifts, foreclosures, family) normally go
    # BELOW market, so one far above the assessment is worth a look. Same
    # explanation rules as the comps screen.
    nonarm = [r for r in rows if "(4)" in r["conv"] and r["restype"] in ("SF", "TH") and r["assessed"] > 0
              and r["price"] >= NONARM_RATIO * r["assessed"]]
    for r in nonarm:
        r["ratio"] = round(r["price"] / r["assessed"], 2)
    explain(nonarm)
    report.update(nonarm_houses=sum(1 for r in rows if "(4)" in r["conv"] and r["restype"] in ("SF", "TH")),
                  nonarm_high=len(nonarm), nonarm_high_explained=sum(1 for r in nonarm if r["explained"]))
    report.update(houses_with_enough_comps=n_eval, candidates=len(cands),
                  explained=sum(1 for r in cands if r["explained"]))
    json.dump({"report": report, "candidates": cands, "nonarm_high": nonarm}, open(os.path.join(CACHE, "screen.json"), "w"), indent=1)
    print(json.dumps(report, indent=1))
    print("\nCandidates NOT explained (by gap over comps median):")
    for r in sorted([r for r in cands if not r["explained"]], key=lambda r: -(r["price"] - r["comps_median"])):
        prev = f"prev {r['prev_date']} ${r['prev_price']:,.0f}" if r.get("prev_date") else "no prior sale"
        print(f"  {r['county'][:4]} {r['date']} ${r['price']:>10,.0f}  comps median ${r['comps_median']:>10,.0f} (n={r['n_comps']}, "
              f"{r['n_higher']} higher)  $/sf x{r['ppsf_mult']}  assessed ${r['assessed']:,.0f} (x{r['ratio']})  built {r['yrblt']}  {prev}  {r['address']}")


    print(f"\nNon-arms-length (4) house transfers at >= {NONARM_RATIO}x assessment, NOT explained:")
    for r in sorted([r for r in nonarm if not r["explained"]], key=lambda r: -r["ratio"]):
        prev = f"prev {r['prev_date']} ${r['prev_price']:,.0f}" if r.get("prev_date") else "no prior sale"
        print(f"  {r['county'][:4]} {r['date']} ${r['price']:>10,.0f} x{r['ratio']} vs ${r['assessed']:,.0f}  built {r['yrblt']}  {prev}  {r['address']}")


if __name__ == "__main__":
    main()
