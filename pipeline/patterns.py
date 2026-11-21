"""
DC pattern screens beyond "high price on a 2025+ house sale".

Why (2026-11-21 review): the first screens were built around one case (a house
delisted, then sold off-market far above its last asking price). The next case
won't look the same. A favor through real estate is value moving between buyer
and seller at a price the market wouldn't set, and it can show up in several
shapes. This script runs one screen per shape, all on public OTR data, no names:

  A. comps_both_ways  2025+ house AND condo sales priced far ABOVE or far BELOW
                      comparable sales in the same assessment neighborhood. Low
                      side = a discount to the buyer (the official as buyer).
  B. otr_unusual      2025+ single-property sales that OTR itself coded 04
                      "Unusual", priced >= 1.3x the pre-sale assessment. OTR coded
                      the press-report sale this way (checked 2026-11-21); this
                      uses the tax office's own review the way the Fairfax screen
                      uses the Fairfax assessor's.
  C. resold_lower     a purchase (2015+) whose buyer later resold, in an ordinary
                      market sale, for far less than the market moved. The later
                      loss is evidence the first price was above market, whatever
                      the first sale looked like at the time.

Descriptors added to every candidate whose sale is the CURRENT owner's purchase
(ITSPE SALEDATE/SALEPRICE match): homestead deduction claimed now (HSTDCODE),
tax-escrow servicer on file now (a mortgage with escrow; absence = cash or no
escrow), and OTR's text label. These describe the holding, never the holder.
The press-report sale has: code 04 Unusual, no homestead, no escrow servicer.
They are descriptors, not filters: most no-homestead buyers are landlords or
second-home owners, and escrow is optional on many loans.

Sale codes (mapped 2026-11-21 by matching each property's latest sale to ITSPE
ACCEPTCODE; 117,815 of 117,898 matched, each code >99.9% one label):
  01 Market Sale, 02 Unassessed, 03 Buyer = Seller, 04 Unusual, 05 Foreclosure,
  06 Government Purchase, 07 Speculative, 08 Miscellaneous, 09 Land Sale,
  T1 Tax Deed, M* the multi-property versions (whole price on every row).

Inputs: .cache/sales_2015.json (pull_history.py), .cache/parcels.json
(pull_parcels.py), DC permits (FEEDS/DCRA, via screen_candidates).
    python3 patterns.py  ->  .cache/patterns.json + printed summary
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from screen_candidates import construction_permits  # noqa: E402

CACHE = os.path.join(HERE, ".cache")
LABEL = {"01": "Market Sale", "02": "Unassessed", "03": "Buyer = Seller", "04": "Unusual", "05": "Foreclosure",
         "06": "Government Purchase", "07": "Speculative", "08": "Miscellaneous", "09": "Land Sale", "T1": "Tax Deed"}
HOUSE, CONDO = {"011", "012", "013"}, {"016", "017"}
# Codes that are never a negotiated price between two private parties.
NOT_ARMS = {"02", "03", "05", "06", "09", "T1"}
SINCE = "2025-01-01"
MIN_COMPS, MAX_BEYOND, MULT = 10, 1, 1.3        # same as screen_candidates (high side)
WINDOW = 183
UNUSUAL_RATIO = 1.3
LOSS_FRAC = 0.75     # resale ratio <= 75% of the market's ratio for the same years
MAX_NOMINAL = 0.85   # and an actual loss of at least 15%
MIN_PAIRS_CELL = 30


def load():
    P = json.load(open(os.path.join(CACHE, "parcels.json")))
    it = {r["SSL"]: r for r in P["itspe"]}
    years = Counter(r.get("CY1YEAR") for r in P["itspe"]).most_common(1)[0][0]
    if years != "2026":
        raise SystemExit(f"CY1YEAR is {years}; the OLDTOTAL/NEWTOTAL mapping assumes 2026")
    size = {}
    for c in P["res"]:
        s = size.setdefault(c["SSL"], {"sqft": 0.0, "bed": 0, "ayb": None})
        s["sqft"] += float(c.get("GBA") or 0)
        s["bed"] = max(s["bed"], int(c.get("BEDRM") or 0))
        s["ayb"] = s["ayb"] or c.get("AYB")
    for c in P["condo"]:
        size[c["SSL"]] = {"sqft": float(c.get("LIVING_GBA") or 0), "bed": int(c.get("BEDRM") or 0), "ayb": c.get("AYB")}
    S = json.load(open(os.path.join(CACHE, "sales_2015.json")))["sales"]
    S = [s for s in S if (s.get("SALE_PRICE") or 0) > 0 and s.get("SALE_CODE") and not s["SALE_CODE"].startswith("M")]
    return it, size, S


def cls(it, ssl):
    u = (it.get(ssl) or {}).get("USECODE")
    return "house" if u in HOUSE else "condo" if u in CONDO else None


def descriptors(it, s):
    r = it.get(s["SSL"]) or {}
    cur = r.get("SALEDATE") == s["SALE_DATE"] and r.get("SALEPRICE") == s["SALE_PRICE"]
    d = {"label": LABEL.get(s["SALE_CODE"], s["SALE_CODE"]), "buyer_is_current_owner": cur,
         "address": r.get("PREMISEADD"), "nbhd": r.get("NBHDNAME"), "use": r.get("USECODE")}
    if cur:
        d["homestead_now"] = r.get("HSTDCODE") is not None
        d["escrow_servicer_now"] = r.get("escrow_servicer")
    return d


def presale_assessment(it, s):
    r = it.get(s["SSL"]) or {}
    return (r.get("OLDTOTAL") if s["SALE_DATE"] < "2026-01-01" else r.get("NEWTOTAL")) or 0


def screen_comps(it, size, S):
    recent = [s for s in S if s["SALE_DATE"] >= SINCE and cls(it, s["SSL"]) and (size.get(s["SSL"]) or {}).get("sqft")]
    pool = defaultdict(list)
    for s in recent:
        if s["QUALIFIED"] == "Q":
            pool[(it[s["SSL"]]["NBHD"], cls(it, s["SSL"]))].append(s)
    out, n_eval = [], Counter()
    for s in recent:
        if s["SALE_CODE"] in NOT_ARMS:
            continue
        me, d0, k = size[s["SSL"]], date.fromisoformat(s["SALE_DATE"]), cls(it, s["SSL"])
        comps = [c for c in pool[(it[s["SSL"]]["NBHD"], k)] if c["SSL"] != s["SSL"]
                 and abs((date.fromisoformat(c["SALE_DATE"]) - d0).days) <= WINDOW
                 and abs(size[c["SSL"]]["sqft"] - me["sqft"]) <= 0.25 * me["sqft"]
                 and abs(size[c["SSL"]]["bed"] - me["bed"]) <= 1]
        if len(comps) < MIN_COMPS:
            continue
        n_eval[k] += 1
        mult = (s["SALE_PRICE"] / me["sqft"]) / statistics.median(c["SALE_PRICE"] / size[c["SSL"]]["sqft"] for c in comps)
        higher = sum(c["SALE_PRICE"] >= s["SALE_PRICE"] for c in comps)
        lower = sum(c["SALE_PRICE"] <= s["SALE_PRICE"] for c in comps)
        side = ("high" if higher <= MAX_BEYOND and mult >= MULT else
                "low" if lower <= MAX_BEYOND and mult <= 1 / MULT else None)
        if side:
            out.append({"screen": "comps_both_ways", "side": side, "class": k, "ssl": s["SSL"], "date": s["SALE_DATE"],
                        "price": s["SALE_PRICE"], "code": s["SALE_CODE"], "q": s["QUALIFIED"], "n_comps": len(comps),
                        "comps_median": statistics.median(c["SALE_PRICE"] for c in comps), "ppsf_mult": round(mult, 2),
                        "sqft": me["sqft"], "year_built": me["ayb"], **descriptors(it, s)})
    return out, dict(n_eval)


def screen_unusual(it, size, S):
    out, n = [], 0
    for s in S:
        if s["SALE_DATE"] < SINCE or s["SALE_CODE"] != "04":
            continue
        n += 1
        a = presale_assessment(it, s)
        if a and s["SALE_PRICE"] >= UNUSUAL_RATIO * a:
            out.append({"screen": "otr_unusual", "class": cls(it, s["SSL"]), "ssl": s["SSL"], "date": s["SALE_DATE"],
                        "price": s["SALE_PRICE"], "code": "04", "assessed_pre_sale": a, "ratio": round(s["SALE_PRICE"] / a, 2),
                        "year_built": (size.get(s["SSL"]) or {}).get("ayb"), "land_area": (it.get(s["SSL"]) or {}).get("LANDAREA"),
                        **descriptors(it, s)})
    return out, n


def screen_resold_lower(it, size, S):
    by = defaultdict(list)
    for s in S:
        if cls(it, s["SSL"]):
            by[s["SSL"]].append(s)
    pairs = []
    for ssl, ss in by.items():
        ss.sort(key=lambda s: s["SALE_DATE"])
        for a, b in zip(ss, ss[1:]):
            # b must be an ordinary market resale; a can be anything a buyer
            # actually paid for (an overpayment might well be coded Unusual).
            if b["SALE_CODE"] != "01" or a["SALE_CODE"] in NOT_ARMS:
                continue
            yrs = (date.fromisoformat(b["SALE_DATE"]) - date.fromisoformat(a["SALE_DATE"])).days / 365.25
            if yrs < 0.5:
                continue
            pairs.append((ssl, a, b, yrs, b["SALE_PRICE"] / a["SALE_PRICE"]))
    # Market's ratio for the same class and the same (buy year, sell year),
    # from market-to-market pairs.
    # Baseline only from holds of 2+ years: short market-to-market pairs are
    # dominated by renovation flips (houses bought 2023, resold 2024: median
    # +44%), which made flat resales look like large losses (first run 2026-11-21).
    cell = defaultdict(list)
    for ssl, a, b, yrs, r in pairs:
        if a["SALE_CODE"] == "01" and yrs >= 2:
            cell[(cls(it, ssl), a["SALE_DATE"][:4], b["SALE_DATE"][:4])].append(r)
    med = {k: statistics.median(v) for k, v in cell.items() if len(v) >= MIN_PAIRS_CELL}
    out, n_eval = [], 0
    for ssl, a, b, yrs, r in pairs:
        # A real nominal loss is required; where a 2+-year baseline exists for
        # the same years, the loss must also be far below it (condo prices fell
        # in some years, so a nominal loss alone can be the market).
        m = med.get((cls(it, ssl), a["SALE_DATE"][:4], b["SALE_DATE"][:4]))
        n_eval += 1
        if r <= MAX_NOMINAL and (m is None or r <= LOSS_FRAC * m):
            sz = size.get(ssl) or {}
            out.append({"screen": "resold_lower", "class": cls(it, ssl), "ssl": ssl, "date": a["SALE_DATE"],
                        "price": a["SALE_PRICE"], "code": a["SALE_CODE"], "resale_date": b["SALE_DATE"],
                        "resale_price": b["SALE_PRICE"], "years": round(yrs, 2), "ratio": round(r, 3),
                        "market_ratio": round(m, 3) if m else None, "year_built": sz.get("ayb"),
                        "label": LABEL.get(a["SALE_CODE"]), "address": (it.get(ssl) or {}).get("PREMISEADD"),
                        "nbhd": (it.get(ssl) or {}).get("NBHDNAME")})
    return out, n_eval, len(med)


def explain(rows, it):
    """Ordinary explanations, each recorded as a reason; nothing is dropped."""
    perms = construction_permits({r["ssl"] for r in rows})
    for r in rows:
        d0 = date.fromisoformat(r["date"])
        yb = r.get("year_built")
        win = []
        if r["screen"] == "resold_lower":
            # New-building premium: buying new from a developer and reselling
            # used is a routine loss, especially for condos.
            if yb and yb >= d0.year - 1:
                r["explained"] = f"bought new (built {yb})"
            continue
        if r.get("side") == "low":
            # A fixer bought cheap shows construction permits AFTER the purchase.
            hi = (d0 + timedelta(days=365)).isoformat()
            win = [p for p in perms.get(r["ssl"], []) if r["date"] <= p[0] <= hi]
            if win:
                r["explained"] = "construction permit within a year after purchase (bought to renovate)"
        else:
            lo = (d0 - timedelta(days=730)).isoformat()
            win = [p for p in perms.get(r["ssl"], []) if lo <= p[0] <= r["date"]]
            if win:
                r["explained"] = "construction permit in the two years before the sale"
            elif yb and yb >= d0.year - 1:
                r["explained"] = f"new construction (built {yb})"
        r["permits"] = win[:5]
    return rows


def main():
    it, size, S = load()
    A, nA = screen_comps(it, size, S)
    B, nB = screen_unusual(it, size, S)
    C, nC, ncell = screen_resold_lower(it, size, S)
    # C only matters while the permit layers cover the window (2023+); it gets
    # no permit lookup (layers before 2023 aren't wired), only the new-build rule.
    rows = explain(A + B + C, it)
    rep = {"sales_2015_single_property": len(S), "comps_evaluated": nA, "unusual_2025_plus": nB,
           "resale_pairs_evaluated": nC, "market_cells": ncell,
           "candidates": Counter(f"{r['screen']}:{r.get('side', '')}:{r['class']}" for r in rows),
           "explained": Counter(f"{r['screen']}:{r.get('side', '')}" for r in rows if r.get("explained")),
           "params": {"MIN_COMPS": MIN_COMPS, "MULT": MULT, "UNUSUAL_RATIO": UNUSUAL_RATIO, "LOSS_FRAC": LOSS_FRAC, "MAX_NOMINAL": MAX_NOMINAL}}
    json.dump({"report": rep, "rows": rows}, open(os.path.join(CACHE, "patterns.json"), "w"), indent=1, default=str)
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
