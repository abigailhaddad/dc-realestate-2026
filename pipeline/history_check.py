"""
Automatic "own sale history" check for shortlisted sales.

Why (2026-11-21): in the hand-run listing checks, two "no listing found" sales
(2823 Q St NW, 400 South Capitol St SE) turned out to be houses whose price had
risen steadily across every recorded sale; the comps screen had flagged them
only because DC's CAMA size understates them. Checking the property's own
history first saves a web search and avoids calling an ordinary sale odd.

Rule: a sale is "consistent with its own history" when the previous recorded
sale of the same SSL (any code except multi-property 'M*', price > 0) is at
least MIN_YEARS earlier and the compound annual growth since then is at most
MAX_CAGR. Quick resales (< MIN_YEARS) are never explained by this rule.

    python3 history_check.py   ->  .cache/history_checks.json

Reads every unchecked sale on the shortlist (listing_checks.shortlist()).
No owner names.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pull import http_get, in_chunks, PROPERTY_SALES  # noqa: E402
import listing_checks  # noqa: E402

CACHE = os.path.join(HERE, ".cache")
MIN_YEARS, MAX_CAGR = 1.0, 0.08


def histories(ssls):
    out = {}
    for chunk in in_chunks(sorted(ssls), 150):
        inl = ",".join("'" + s.replace("'", "''") + "'" for s in chunk)
        offset = 0
        while True:
            r = http_get(f"{PROPERTY_SALES}/query", {"where": f"SSL IN ({inl})", "outFields": "SSL,SALE_DATE,SALE_PRICE,SALE_CODE",
                                                     "returnGeometry": "false", "f": "json", "resultOffset": offset,
                                                     "resultRecordCount": 2000})
            if "error" in r:
                raise RuntimeError(r["error"])
            f = r.get("features", [])
            for x in f:
                a = x["attributes"]
                if a.get("SALE_DATE") is None:
                    continue
                d = datetime.fromtimestamp(a["SALE_DATE"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                out.setdefault(a["SSL"], []).append((d, a.get("SALE_PRICE") or 0, a.get("SALE_CODE") or ""))
            if len(f) < 2000 and not r.get("exceededTransferLimit"):
                break
            offset += len(f)
    return {k: sorted(v) for k, v in out.items()}


def main():
    rows = listing_checks.shortlist()
    done = listing_checks.load_listings()
    todo = [r for k, r in rows.items() if k not in done]
    hist = histories({r["ssl"] for r in todo})
    out = []
    for r in todo:
        prior = [h for h in hist.get(r["ssl"], []) if h[0] < r["sale_date"] and h[1] > 0 and not h[2].startswith("M")]
        rec = {"ssl": r["ssl"], "sale_date": r["sale_date"], "price": r["price"], "address": r["address"],
               "history": hist.get(r["ssl"], [])}
        if prior:
            pd, pp, pc = prior[-1]
            yrs = (date.fromisoformat(r["sale_date"]) - date.fromisoformat(pd)).days / 365.25
            cagr = (r["price"] / pp) ** (1 / yrs) - 1 if yrs > 0 else None
            rec.update(prev_date=pd, prev_price=pp, years=round(yrs, 2), cagr=round(cagr, 4) if cagr is not None else None)
            rec["consistent"] = bool(yrs >= MIN_YEARS and cagr is not None and cagr <= MAX_CAGR)
        else:
            rec["consistent"] = False
        out.append(rec)
    json.dump({"params": {"MIN_YEARS": MIN_YEARS, "MAX_CAGR": MAX_CAGR}, "checks": out},
              open(os.path.join(CACHE, "history_checks.json"), "w"), indent=1)
    n = sum(r["consistent"] for r in out)
    print(f"{len(out)} unchecked sales; {n} consistent with their own sale history; {len(out) - n} still need a listing check")
    for r in sorted(out, key=lambda r: (r["consistent"], r["sale_date"])):
        prev = f"prev {r['prev_date']} ${r['prev_price']:,.0f} ({r['years']}y, {100 * r['cagr']:.1f}%/yr)" if "prev_date" in r else "no prior sale"
        print(f"  {'explained' if r['consistent'] else 'NEEDS CHECK':11} {r['sale_date']} ${r['price']:>10,.0f}  {r['address'].split(' WASHINGTON')[0]:28} {prev}")


if __name__ == "__main__":
    main()
