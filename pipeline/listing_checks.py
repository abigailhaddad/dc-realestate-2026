"""
Listing check for shortlisted sales: was the house on the open market, and how
did the sale price compare with the last asking price?

Why this step exists (2026-11-20): DC's own data can't separate an anomalous
sale from a large renovated or rebuilt house. Its CAMA size and year-built fields
lag renovations (listings showed 4,512 vs DC's much smaller GBA; a 2024 rebuild
still carried the old house's record), so a comps screen surfaces many new and
renovated homes. Every one of the first 14 such sales checked had been publicly
listed and sold at, below, or near its asking price. The motivating case
(610 Independence Ave SE) was the opposite: listed, cut, delisted, then sold
off-market well above the last asking price.

Listing history lives in the brokers' MLS and on Zillow / Redfin, which forbid
scraping, so this step is NOT automated. Each check is one web search per
address, recorded by hand (or by an assistant) in LISTINGS with its source URLs.
This script lists what still needs checking and classifies what has been checked.

    python3 listing_checks.py todo        # shortlisted sales with no listing check yet
    python3 listing_checks.py classify    # verdict per sale -> .cache/shortlist.json

Inputs: .cache/comps_screen.json (and .cache/flag_overpriced.json 'flagged').
LISTINGS lives in .cache/listing_checks.json (gitignored: a list of flagged homes
should not be published from a public repo). No owner names anywhere.

Verdicts:
  cleared        listed and sold at or below the last asking price, or a lender sale
  normal_bidding listed and sold above the last asking price by less than 10%
  keep           sold off-market (delisted first, or no listing found), or >= 10%
                 above the last asking price
  explained      off-market, but a primary record explains the price (raze, addition / renovation
                 permits between the purchase and the resale, or barely changed since the last sale)
  unchecked      no listing check recorded yet
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
LISTINGS = os.path.join(CACHE, "listing_checks.json")
OVER_ASK_KEEP = 0.10


def shortlist():
    rows = {}
    p = os.path.join(CACHE, "comps_screen.json")
    if os.path.exists(p):
        for x in json.load(open(p)):
            rows[(x["ssl"], x["date"])] = {"ssl": x["ssl"], "sale_date": x["date"], "price": x["price"],
                                           "address": x["addr"], "sale_code": x["code"], "source": "comps_screen"}
    p = os.path.join(CACHE, "screen_v2.json")
    if os.path.exists(p):
        for x in json.load(open(p))["kept"]:
            rows.setdefault((x["ssl"], x["date"]), {"ssl": x["ssl"], "sale_date": x["date"], "price": x["price"],
                                                    "address": x["address"], "sale_code": x["code"], "source": "screen_v2"})
    p = os.path.join(CACHE, "flag_overpriced.json")
    if os.path.exists(p):
        for r in json.load(open(p))["flagged"]:
            if r.get("class") == "house" and r["n_properties"] == 1:
                k = (r["ssls"][0], r["sale_date"])
                rows.setdefault(k, {"ssl": k[0], "sale_date": k[1], "price": r["price"], "address": r["address"],
                                    "sale_code": ",".join(r["sale_codes"]), "source": "assessment_flag"})
    return rows


def load_listings():
    if not os.path.exists(LISTINGS):
        return {}
    return {(e["ssl"], e["sale_date"]): e for e in json.load(open(LISTINGS))}


def verdict(sale, e):
    if not e:
        return "unchecked", "no listing check recorded"
    if e.get("lender_sale"):
        return "cleared", "lender sale / foreclosure take-back"
    if e.get("explained_by"):
        # Set by hand from a primary record (e.g. a DC building permit), with the
        # permit or record named in notes. Off-market alone isn't suspicious when
        # the price change has a documented cause.
        return "explained", e["explained_by"]
    if not e.get("listed"):
        return "keep", "no public listing found (possible off-market sale)"
    ask = e.get("last_ask")
    if e.get("delisted_before_sale"):
        if ask and sale["price"] > ask:
            return "keep", f"delisted, then sold {100 * (sale['price'] / ask - 1):.0f}% above the last asking price"
        return "keep", "delisted before the sale"
    if not ask:
        return "cleared", "publicly listed (asking price not found)"
    over = sale["price"] / ask - 1
    if over <= 0:
        return "cleared", ("listed; sold at asking" if abs(over) < 0.0005 else f"listed; sold {100 * -over:.1f}% below asking")
    if over < OVER_ASK_KEEP:
        return "normal_bidding", f"listed; sold {100 * over:.1f}% above asking"
    return "keep", f"listed; sold {100 * over:.0f}% above asking"


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "classify"
    rows, lst = shortlist(), load_listings()
    if cmd == "todo":
        todo = [r for k, r in sorted(rows.items(), key=lambda kv: kv[1]["sale_date"]) if k not in lst]
        for r in todo:
            # .title() would write "49Th"; capitalize words without touching ordinals.
            addr = " ".join(w if w[:1].isdigit() else w.capitalize() for w in r["address"].split(" WASHINGTON")[0].split())
            print(f"{r['ssl']!r} {r['sale_date']} ${r['price']:,.0f}  search: \"{addr}\" Washington DC sold {r['sale_date'][:4]} list price")
        print(f"\n{len(todo)} of {len(rows)} still need a listing check")
        return
    hist = {}
    hp = os.path.join(CACHE, "history_checks.json")
    if os.path.exists(hp):
        hist = {(h["ssl"], h["sale_date"]): h for h in json.load(open(hp))["checks"]}
    out = []
    for k, r in rows.items():
        v, why = verdict(r, lst.get(k))
        h = hist.get(k)
        if v == "unchecked" and h and h.get("consistent"):
            # history_check.py: previous sale >= 1 year earlier, <= 8%/yr since.
            v, why = "explained", (f"consistent with its own sale history: ${h['prev_price']:,.0f} on {h['prev_date']}, "
                                   f"{100 * h['cagr']:.1f}%/yr since (auto)")
        out.append({**r, "verdict": v, "why": why, "listing": lst.get(k)})
    order = {"keep": 0, "unchecked": 1, "explained": 2, "normal_bidding": 3, "cleared": 4}
    out.sort(key=lambda x: (order[x["verdict"]], x["sale_date"]))
    with open(os.path.join(CACHE, "shortlist.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    from collections import Counter
    print(dict(Counter(x["verdict"] for x in out)))
    for x in out:
        print(f"  {x['verdict']:14} {x['sale_date']} ${x['price']:>11,.0f}  {x['address'].split(' WASHINGTON')[0]:30} {x['why']}")


if __name__ == "__main__":
    main()
