"""
Single daily entrypoint for the price-anomaly screen: DC, Arlington (VA),
Montgomery + Prince George's (MD), and Fairfax (VA).

Runs the full chain in dependency order, matching docs/overpriced_sales.md's
"Rerunning" section (this script replaces running those commands by hand):

  1. Pull fresh inputs       pull_flag_inputs.py, pull_history.py, pull_parcels.py
  2. Price-anomaly screens   flag_overpriced.py, screen_candidates.py, patterns.py
  3. Ordinary-explanation    history_check.py, listing_checks.py (todo + classify)
  4. County screens (each one pulls, screens, and explains in a single script)
                             counties/arlington.py, counties/maryland.py,
                             counties/fairfax.py
  5. One legible summary     docs/daily_status.md (overwritten each run) and
                             data/daily_status.json (small, committed aggregate)

Deliberately NOT part of this chain (manual, local-only; never run in CI, never
committed): pipeline/officials.py, pipeline/officials_dc_tax.py,
pipeline/check_flagged.py. Those look up ownership / the DC corporate registry
and write owner names to pipeline/.cache/, which is gitignored on purpose.

No owner, buyer, or seller name is read, computed, or written anywhere in this
script. Addresses, prices, and dates are public property records already
discussed by address in docs/overpriced_sales.md; nothing else identifying is
added. See each called script's own docstring for exactly which fields it
does and doesn't request.

    python3 run_daily.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CACHE = os.path.join(HERE, ".cache")
DATA_DIR = os.path.join(REPO, "data")
DOCS_DIR = os.path.join(REPO, "docs")

STATUS_MD = os.path.join(DOCS_DIR, "daily_status.md")
STATUS_JSON = os.path.join(DATA_DIR, "daily_status.json")

# Run order. Each entry is a path relative to pipeline/, invoked as its own
# `python3` process (matching how every script here is designed to be run,
# and keeping each one's module-level globals from leaking into the others).
STEPS = [
    ("pull_flag_inputs.py", []),
    ("pull_history.py", []),
    ("pull_parcels.py", []),
    ("flag_overpriced.py", []),
    ("screen_candidates.py", []),
    ("history_check.py", []),
    ("listing_checks.py", ["todo"]),       # prints what still needs a manual search
    ("listing_checks.py", ["classify"]),   # writes .cache/shortlist.json
    ("patterns.py", []),
    (os.path.join("counties", "arlington.py"), []),
    (os.path.join("counties", "maryland.py"), []),
    (os.path.join("counties", "fairfax.py"), []),
]


def run_step(script, args):
    path = os.path.join(HERE, script)
    label = f"python3 {script} {' '.join(args)}".strip()
    print(f"\n{'=' * 70}\n$ {label}\n{'=' * 70}", flush=True)
    t0 = time.time()
    subprocess.run([sys.executable, path, *args], cwd=HERE, check=True)
    print(f"[{label} — {time.time() - t0:.0f}s]", flush=True)


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as fh:
        return json.load(fh)


def money(x):
    return f"${x:,.0f}" if x is not None else "?"


# ---------------------------------------------------------------------------
# Build one flat list of "candidates": every sale any screen flagged, with
# a stable key (for diffing against yesterday's run), whether an automated
# check found an ordinary explanation, and why -- or why not.
# ---------------------------------------------------------------------------

def dc_candidates():
    out = []

    # Main DC screen (assessment ratio + wider comps), with history/listing
    # checks layered on. shortlist.json already merges flag_overpriced.py's
    # flagged HOUSE sales with screen_candidates.py's wider comps candidates,
    # deduped by (ssl, date), and carries the listing/history verdict, but
    # NOT the magnitude that got it flagged in the first place -- look that
    # back up from whichever of the two screens originally found it.
    screen_v2 = load(os.path.join(CACHE, "screen_v2.json"), {})
    screen_v2_by_key = {(r["ssl"], r["date"]): r for r in screen_v2.get("kept", []) + screen_v2.get("dropped", [])}
    fo_flagged = load(os.path.join(CACHE, "flag_overpriced.json"), {}).get("flagged", [])
    fo_by_key = {(s, r["sale_date"]): r for r in fo_flagged for s in r.get("ssls", [])}

    shortlist = load(os.path.join(CACHE, "shortlist.json"), [])
    for r in shortlist:
        explained = r["verdict"] in ("explained", "cleared", "normal_bidding")
        k = (r["ssl"], r["sale_date"])
        v2, fo_r = screen_v2_by_key.get(k), fo_by_key.get(k)
        if fo_r:
            flag_reason = (f"{fo_r['ratio_vs_peers']:.1f}x the {fo_r['peer_level']} peer price/assessment ratio, "
                           f"{money(fo_r['price'] - fo_r['assessed'])} over assessment")
        elif v2:
            flag_reason = f"{v2['ppsf_mult']}x comps' $/sqft, {v2['n_comps']} comparables"
        else:
            flag_reason = f"sale code {r.get('sale_code')}"
        out.append({
            "jurisdiction": "DC", "screen": "assessment + comps (house)",
            "key": f"DC|house|{r['ssl']}|{r['sale_date']}",
            "date": r["sale_date"], "price": r["price"], "address": r.get("address"),
            "flag_reason": flag_reason,
            "explained": explained,
            "reason": r["why"] if explained else f"{r['verdict']}: {r['why']}",
        })

    # flag_overpriced.py's "flagged": sales at >= 2x the neighborhood/citywide
    # peer ratio AND >= $100K over assessment, with flag_overpriced.py's own
    # ordinary-explanation checks already applied (new construction, vacant
    # land, multi-property mismatch, next assessment catching up -- those are
    # excluded from "flagged" already). Only the single-property HOUSE ones
    # get a further history/listing check (above, via shortlist.json). Every
    # other class -- condo, multifamily, mixed, vacant, parking, other, and
    # every multi-property deal -- has NO further automated check in this
    # chain: it is reported here as still open, not quietly dropped.
    fo = load(os.path.join(CACHE, "flag_overpriced.json"), {})
    for r in fo.get("flagged", []):
        if r.get("class") == "house" and r.get("n_properties") == 1:
            continue  # already covered via shortlist.json above
        out.append({
            "jurisdiction": "DC", "screen": f"assessment ratio ({r.get('class')})",
            "key": "DC|{}|{}|{}".format(r.get("class"), "-".join(r.get("ssls", [])), r["sale_date"]),
            "date": r["sale_date"], "price": r["price"], "address": r.get("address"),
            "flag_reason": f"{r['ratio_vs_peers']:.1f}x the {r['peer_level']} peer price/assessment "
                           f"ratio, {money(r['price'] - r['assessed'])} over assessment",
            "explained": False,
            "reason": "not a single-property house sale, so history_check.py / listing_checks.py "
                      "never ran on it -- no automated ordinary-explanation check exists for this class yet",
        })

    # patterns.py: three more DC screens, each with its own inline explanation.
    pat = load(os.path.join(CACHE, "patterns.json"), {})
    for r in pat.get("rows", []):
        screen = {"comps_both_ways": f"comps, {r.get('side')} side ({r.get('class')})",
                  "otr_unusual": "OTR 'Unusual' sale code",
                  "resold_lower": "bought high, resold lower"}.get(r["screen"], r["screen"])
        explained = bool(r.get("explained"))
        if r["screen"] == "resold_lower":
            flag_reason = (f"resold {r['resale_date']} for {money(r['resale_price'])}, "
                           f"{100 * (1 - r['ratio']):.0f}% below the {r['date']} purchase price")
        elif r["screen"] == "otr_unusual":
            flag_reason = f"OTR-coded Unusual sale at {r['ratio']}x the pre-sale assessment"
        else:
            flag_reason = f"{r['ppsf_mult']}x comps' $/sqft, {r['n_comps']} comparables"
        out.append({
            "jurisdiction": "DC", "screen": screen,
            "key": f"DC|{r['screen']}|{r.get('side', '')}|{r['ssl']}|{r['date']}",
            "date": r["date"], "price": r["price"], "address": r.get("address"),
            "flag_reason": flag_reason, "explained": explained,
            "reason": r.get("explained") or "no automated explanation found",
        })
    return out


def county_candidates():
    out = []

    arl = load(os.path.join(CACHE, "arlington", "screen.json"), {})
    for r in arl.get("candidates", []):
        out.append({
            "jurisdiction": "Arlington, VA", "screen": "comps",
            "key": f"ARL|comps|{r['rpc']}|{r['date']}",
            "date": r["date"], "price": r["price"], "address": r.get("address"),
            "flag_reason": f"{r['ppsf_mult']}x comps' $/sqft, {r['n_comps']} comparables",
            "explained": bool(r.get("explained")), "reason": r.get("explained") or "no automated explanation found",
        })
    for r in arl.get("assessor_not_market_high", []):
        out.append({
            "jurisdiction": "Arlington, VA", "screen": "assessor-coded 'not a market sale' (N)",
            "key": f"ARL|assessor_n|{r['rpc']}|{r['date']}",
            "date": r["date"], "price": r["price"], "address": r.get("address"),
            "flag_reason": f"{r['ratio']}x the pre-sale assessment", "explained": bool(r.get("explained")),
            "reason": r.get("explained") or "no automated explanation found",
        })
    # County-coded "not listed MLS" sales far above assessment: printed by the
    # script itself as worth a look, but it runs no explanation check on them
    # at all (not even the ones above). Reported here as unexplained, clearly
    # labeled, rather than silently left out of the summary.
    for r in arl.get("county_coded_not_listed", []):
        if r.get("ratio") and r["ratio"] >= 1.5:
            out.append({
                "jurisdiction": "Arlington, VA", "screen": "county-coded off-market (no explanation check run)",
                "key": f"ARL|off_mkt|{r['rpc']}|{r['date']}",
                "date": r["date"], "price": r["price"], "address": r.get("address"),
                "flag_reason": f"{r['ratio']:.2f}x assessment, county-coded 'not listed MLS/online'",
                "explained": False, "reason": "this screen has no automated explanation check",
            })

    md = load(os.path.join(CACHE, "maryland", "screen.json"), {})
    for r in md.get("candidates", []):
        out.append({
            "jurisdiction": f"{r['county']}, MD", "screen": "comps",
            "key": f"MD|comps|{r['acct']}|{r['date']}",
            "date": r["date"], "price": r["price"], "address": r.get("address"),
            "flag_reason": f"{r['ppsf_mult']}x comps' $/sqft, {r.get('n_comps')} comparables",
            "explained": bool(r.get("explained")), "reason": r.get("explained") or "no automated explanation found",
        })
    for r in md.get("nonarm_high", []):
        out.append({
            "jurisdiction": f"{r['county']}, MD", "screen": "non-arms-length, priced above assessment",
            "key": f"MD|nonarm|{r['acct']}|{r['date']}",
            "date": r["date"], "price": r["price"], "address": r.get("address"),
            "flag_reason": f"{r['ratio']}x assessment on a non-arms-length transfer",
            "explained": bool(r.get("explained")), "reason": r.get("explained") or "no automated explanation found",
        })

    fx = load(os.path.join(CACHE, "fairfax", "screen.json"), {})
    for r in fx.get("kept", []):  # "kept" = NOT set aside, i.e. still unexplained by construction
        out.append({
            "jurisdiction": "Fairfax, VA", "screen": "assessor-coded atypical",
            "key": f"FX|atypical|{r['parid']}|{r['date']}",
            "date": r["date"], "price": r["price"], "address": r.get("address"),
            "flag_reason": f"{r['ratio']}x pre-sale assessment, assessor code '{r['code']}'",
            "explained": False, "reason": "no automated explanation found",
        })
    return out


def as_of_dates():
    """Latest sale date each jurisdiction's pull actually reached -- not when
    this script ran, which may be hours or days after the source refreshed."""
    d = {}
    fi = load(os.path.join(CACHE, "flag_inputs.json"))
    if fi and fi.get("sales"):
        d["DC"] = max(s["SALE_DATE"] for s in fi["sales"] if s.get("SALE_DATE"))
    arl = load(os.path.join(CACHE, "arlington", "screen.json"))
    if arl:
        d["Arlington, VA"] = arl.get("report", {}).get("latest_sale_date")
    md = load(os.path.join(CACHE, "maryland", "screen.json"))
    if md:
        d["Montgomery + Prince George's, MD"] = md.get("report", {}).get("latest_transfer")
    fx = load(os.path.join(CACHE, "fairfax", "screen.json"))
    if fx:
        d["Fairfax, VA"] = fx.get("report", {}).get("latest_sale")
    return d


def pulled_counts():
    """Total 2025+ sales each jurisdiction's pull currently sees -- used to
    diff against yesterday's run and report how many NEW sales came in."""
    d = {}
    fi = load(os.path.join(CACHE, "flag_inputs.json"))
    if fi:
        d["DC"] = len(fi.get("sales", []))
    arl = load(os.path.join(CACHE, "arlington", "screen.json"))
    if arl:
        d["Arlington, VA"] = arl.get("report", {}).get("sales_2025_plus_price_gt0")
    md = load(os.path.join(CACHE, "maryland", "screen.json"))
    if md:
        d["Montgomery + Prince George's, MD"] = md.get("report", {}).get("rows_with_2025_26_transfer")
    fx = load(os.path.join(CACHE, "fairfax", "screen.json"))
    if fx:
        d["Fairfax, VA"] = fx.get("report", {}).get("sales_2025_plus_price_gt0")
    return d


def render_markdown(cands, prev, as_of, pulled):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    unexplained = [c for c in cands if not c["explained"]]
    explained = [c for c in cands if c["explained"]]
    by_jur = Counter(c["jurisdiction"] for c in cands)
    unexp_by_jur = Counter(c["jurisdiction"] for c in unexplained)

    prev_counts = (prev or {}).get("pulled_counts", {})
    new_sales = {j: (pulled.get(j) or 0) - (prev_counts.get(j) or 0) for j in pulled}
    prev_keys = {c["key"] for c in (prev or {}).get("candidates", [])}
    newly_flagged = [c for c in unexplained if c["key"] not in prev_keys]

    lines = []
    lines.append("# Daily price-anomaly screen")
    lines.append("")
    lines.append(f"Last run: {now}. Covers sales from 2025-01-01 through each jurisdiction's "
                 "most recent data pull (below) in DC, Arlington (VA), Montgomery + Prince George's "
                 "(MD), and Fairfax (VA). Full methodology: [`docs/overpriced_sales.md`](./overpriced_sales.md).")
    lines.append("")
    lines.append("**This pipeline flags transactions, never people.** No owner, buyer, or seller name "
                 "is used anywhere in it. A flag is a reason to look, not a finding -- "
                 "most flagged sales turn out to have an ordinary explanation.")
    lines.append("")

    lines.append("## As of this run")
    lines.append("")
    lines.append("| Jurisdiction | Latest sale in the pull | 2025+ sales on file | New since last run |")
    lines.append("|---|---|---|---|")
    for j in ("DC", "Arlington, VA", "Montgomery + Prince George's, MD", "Fairfax, VA"):
        delta = new_sales.get(j)
        delta_s = "n/a (first run)" if prev is None else (f"+{delta}" if delta is not None else "?")
        n = pulled.get(j)
        n_s = f"{n:,}" if isinstance(n, int) else "?"
        lines.append(f"| {j} | {as_of.get(j, '?')} | {n_s} | {delta_s} |")
    lines.append("")

    total_pulled = sum(v for v in pulled.values() if isinstance(v, int))
    total_new = sum(v for v in new_sales.values() if v)
    lines.append(f"**{total_pulled:,} sales on file since 2025-01-01 across all four areas "
                 f"({'+' + str(total_new) + ' new since the last run' if prev is not None else 'first run, no prior count to compare'}).**")
    lines.append("")

    lines.append("## Flagged as price outliers")
    lines.append("")
    lines.append(f"**{len(cands):,} sale/screen combinations flagged** across every screen this run "
                 "(a single sale can be flagged by more than one screen). "
                 f"**{len(explained):,} have an automated ordinary explanation** (new construction, a "
                 "documented construction/renovation permit, consistent with the property's own sale "
                 "history, a farm or large-lot assessment, or a comparable public listing). "
                 f"**{len(unexplained):,} remain unexplained by anything this pipeline checks automatically.**")
    if prev is not None:
        lines.append("")
        lines.append(f"Of those {len(unexplained):,}, **{len(newly_flagged):,} are new since the last run** "
                     "(not already unexplained yesterday).")
    lines.append("")

    lines.append("| Jurisdiction | Flagged (sale/screen combos) | Unexplained |")
    lines.append("|---|---|---|")
    for j, n in by_jur.most_common():
        lines.append(f"| {j} | {n} | {unexp_by_jur.get(j, 0)} |")
    lines.append("")

    lines.append("### What this run does and does not check automatically")
    lines.append("")
    lines.append("- **DC house sales** get the full automated chain: assessment-ratio screen + comps "
                 "screen, then an own-sale-history check, then a manual listing check IF one has already "
                 "been recorded locally (listing checks require a web search and are not run in CI -- "
                 "see `pipeline/listing_checks.py`). On a from-scratch run (e.g. this repo's CI), most "
                 "DC house candidates will show as `unchecked`, not `cleared`: that means no listing "
                 "search has been done yet, not that the sale is suspicious.")
    lines.append("- **DC condos, multifamily, vacant, parking, mixed, and multi-property sales** flagged "
                 "by the assessment-ratio screen get NO further automated check in this pipeline -- "
                 "they are listed below as unexplained by definition.")
    lines.append("- **DC's three pattern screens** (comps both ways, OTR 'Unusual' code, bought-high-"
                 "resold-lower) each carry their own inline explanation check (permits, new construction, "
                 "bought-new).")
    lines.append("- **Arlington / Maryland** comps candidates get own-sale-history, farm/large-lot (MD), "
                 "new-construction, and construction-permit checks. The county-coded 'not listed MLS' "
                 "list (Arlington) gets none of those checks at all.")
    lines.append("- **Fairfax** relies on the county assessor's own 'atypical sale' coding rather than a "
                 "comps screen; everything in `kept` has already had new-construction and remodel-year "
                 "set-asides applied, so everything listed below is genuinely unexplained by this chain.")
    lines.append("")

    def table(rows):
        out_lines = ["| Jurisdiction | Screen | Date | Price | Address | Why flagged |",
                     "|---|---|---|---|---|---|"]
        for c in rows:
            addr = (c["address"] or "?").replace("|", "/")
            out_lines.append(f"| {c['jurisdiction']} | {c['screen']} | {c['date']} | {money(c['price'])} "
                             f"| {addr} | {c['flag_reason']} |")
        return out_lines

    MAX_ROWS = 60  # keep this file skimmable; the full list is in data/daily_status.json

    if prev is not None:
        lines.append("## Newly flagged since the last run")
        lines.append("")
        lines.append("Sales that are unexplained today and were NOT already unexplained on the previous "
                     "run (i.e. either new sales, or newly flagged by a screen). This is the section worth "
                     "reading daily; everything below it is the full accumulated backlog.")
        lines.append("")
        if not newly_flagged:
            lines.append("None.")
        else:
            lines += table(sorted(newly_flagged, key=lambda c: -c["price"])[:MAX_ROWS])
            if len(newly_flagged) > MAX_ROWS:
                lines.append("")
                lines.append(f"_(+{len(newly_flagged) - MAX_ROWS} more newly-flagged, largest shown first; "
                             "full list in `data/daily_status.json`.)_")
        lines.append("")

    lines.append("## All unexplained candidates (largest first)")
    lines.append("")
    if not unexplained:
        lines.append("None this run.")
    else:
        lines.append(f"Address, price, date, and why each was flagged, for all {len(unexplained):,} "
                     "sale/screen combinations this run could not automatically explain. No owner, buyer, "
                     "or seller name is included or was looked up for this list. Showing the "
                     f"{min(MAX_ROWS, len(unexplained))} largest by price" +
                     (f"; the remaining {len(unexplained) - MAX_ROWS:,} are in `data/daily_status.json` "
                      "(same fields, every row)." if len(unexplained) > MAX_ROWS else "."))
        lines.append("")
        lines += table(sorted(unexplained, key=lambda c: -c["price"])[:MAX_ROWS])
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append("- **This is an automated-only pass.** `docs/overpriced_sales.md` describes the same "
                 "screens after a round of manual listing checks, which clear most remaining candidates; "
                 "this file reflects what the code alone can determine as of this run, so its "
                 "'unexplained' count will usually run higher, especially for DC house sales that haven't "
                 "had a one-time manual listing search recorded yet (see `pipeline/listing_checks.py`).")
    lines.append("- **The DC 'comps, low side' screen is known to be noisy.** Per `docs/overpriced_sales.md`, "
                 "a buyer paying far below comparables is dominated by investors buying distressed or "
                 "long-held houses; the underlying analysis there narrowed 970 such sales down to 65 "
                 "worth a listing check using extra filters (condition, not-since-resold) that this "
                 "automated pass does not apply. Treat 'low side' rows below as lower-priority than "
                 "'high side' ones unless and until they get a manual look.")
    lines.append("- **Thresholds are judgment calls** (comps $/sqft multiplier, dollar/ratio floors, "
                 "8%/year appreciation ceiling, days of comp window) -- see each script's docstring in "
                 "`pipeline/` for the exact numbers and why they were chosen.")
    lines.append("- **Coverage.** Comps screens cover houses (and, in DC, condos); multifamily, "
                 "commercial, and most multi-property sales aren't comps-screened in any jurisdiction.")
    lines.append("- **County raw-data caches.** Arlington and Maryland's raw pulls are cached to disk "
                 "and reused if present; a CI run starts from a clean checkout (no cache), so it always "
                 "re-pulls. Running this script repeatedly on a machine with an existing "
                 "`pipeline/.cache/` will reuse stale county data until that cache is deleted.")
    lines.append("- **`pipeline/.cache/comps_screen.json`** is a legacy file from an earlier version of "
                 "this pipeline; nothing currently regenerates it. `listing_checks.py` reads it only if "
                 "present, so its absence on a clean checkout changes nothing going forward.")
    lines.append("")
    lines.append("_Generated by `pipeline/run_daily.py`. Raw screen output (with no owner names) stays "
                 "in `pipeline/.cache/`, which is gitignored and not part of this commit._")
    return "\n".join(lines)


def main():
    t0 = time.time()
    prev = load(STATUS_JSON)  # yesterday's committed summary, if any, for diffing

    for script, args in STEPS:
        run_step(script, args)

    cands = dc_candidates() + county_candidates()
    as_of = as_of_dates()
    pulled = pulled_counts()

    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATUS_MD, "w") as fh:
        fh.write(render_markdown(cands, prev, as_of, pulled))
    # Only unexplained candidates are stored here -- that's the "full list" the
    # markdown promises for anything cut off its display cap, and it's also
    # exactly the right set to diff against next run for "newly flagged"
    # (a sale that was explained yesterday and is unexplained today should
    # count as newly flagged, not get silently matched against yesterday's key).
    unexplained = [c for c in cands if not c["explained"]]
    with open(STATUS_JSON, "w") as fh:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "as_of": as_of, "pulled_counts": pulled,
            "total_flagged": len(cands), "total_unexplained": len(unexplained),
            "flagged_by_jurisdiction": dict(Counter(c["jurisdiction"] for c in cands)),
            "unexplained_by_jurisdiction": dict(Counter(c["jurisdiction"] for c in unexplained)),
            "candidates": unexplained,
        }, fh, indent=1)

    print(f"\nWrote {STATUS_MD} and {STATUS_JSON}")
    print(f"Total runtime: {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
