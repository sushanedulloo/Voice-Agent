#!/usr/bin/env python3
"""Charter features 2-6, as a report and as a dashboard.

    python tools/insights.py --run <run-id>
    python tools/insights.py --run <run-id> --html runs/<run-id>/dashboard.html

Reads only the audit trail. Prints the provenance banner on every invocation, because these
numbers come from simulated calls against synthetic content and the arithmetic being real does
not make the inputs real.
"""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent

from engine import Content                                        # noqa: E402
from engine.audit import Audit                                    # noqa: E402
from engine.insights import (MIN_SAMPLE, best_time_to_call,       # noqa: E402
                             funnel, intelligence_cuts, recommended_windows,
                             sentiment_trends, stt_quality_audit, success_repository)

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def banner(content, calls):
    print(f"\n{'=' * 78}")
    print(f"  INSIGHTS  ·  {len(calls)} calls  ·  pack {content.pack_name} "
          f"({content.provenance})")
    print(f"{'=' * 78}")
    if content.provenance != "blc-approved":
        print("  Synthetic content, simulated dialer, simulated advisor, uncalibrated sentiment.")
        print("  The arithmetic is real. The inputs are not. Do not quote these externally.")


def show_best_time(calls):
    print(f"\n  FEATURE 3 · BEST TIME TO CALL"
          f"   (slices under {MIN_SAMPLE} attempts marked thin)")
    print(f"    {'hour':>5} {'attempts':>9} {'connect':>8} {'95% CI':>16}")
    for r in best_time_to_call(calls, "attempt_hour"):
        thin = "" if r["reliable"] else "  thin"
        print(f"    {r['slice']:>5} {r['attempts']:>9} {r['connect_rate']:>7.1%} "
              f"  [{r['ci_low']:.1%}–{r['ci_high']:.1%}]{thin}")
    rec = recommended_windows(calls)
    if rec:
        hrs = ", ".join(f"{r['slice']}:00 ({r['connect_rate']:.0%})" for r in rec)
        print(f"\n    recommended windows: {hrs}")
        print("    ranked by the LOWER confidence bound, so a lucky small sample cannot win")

    rows = best_time_to_call(calls, "attempt_weekday")
    if rows:
        print(f"\n    {'day':>5} {'attempts':>9} {'connect':>8}")
        for r in rows:
            name = DAYS[r["slice"]] if isinstance(r["slice"], int) and r["slice"] < 7 else r["slice"]
            print(f"    {name:>5} {r['attempts']:>9} {r['connect_rate']:>7.1%}")


def show_cuts(calls):
    print(f"\n  FEATURE 4 · INTELLIGENCE CUTS")
    cuts = intelligence_cuts(calls)
    for field in ("product", "locale", "zone", "persona_tier"):
        data = cuts.get(field) or {}
        if not data:
            continue
        print(f"\n    by {field}")
        print(f"      {'':14} {'att':>6} {'conn':>7} {'agree':>7} {'book':>7} {'contain':>8}")
        for key, d in sorted(data.items(), key=lambda kv: -kv[1]["attempts"]):
            conn = "     -" if d["connect_rate"] is None else f"{d['connect_rate']:>6.1%}"
            print(f"      {str(key):14} {d['attempts']:>6} {conn} "
                  f"{d['agree_rate']:>6.1%} {d['book_rate']:>6.1%} {d['containment']:>7.1%}")


def show_sentiment(calls):
    t = sentiment_trends(calls)
    if not t.get("labels"):
        print("\n  FEATURE 2 · SENTIMENT — no sentiment recorded in this run")
        return
    print(f"\n  FEATURE 2 · SENTIMENT TRENDS   (uncalibrated: {not t['calibrated']})")
    total = sum(t["labels"].values())
    for label, n in t["labels"].items():
        print(f"      {label:12} {n:>6}  {n/total:>6.1%}")
    print(f"      escalating calls: {t['escalating_calls']}")
    if t["booking_rate_by_sentiment"]:
        print(f"\n      booking rate by sentiment (slices >= {MIN_SAMPLE}):")
        for label, rate in sorted(t["booking_rate_by_sentiment"].items(),
                                  key=lambda kv: -kv[1]):
            print(f"        {label:12} {rate:>6.1%}")
        print("      If this ordering is stable it is a triage signal: route the positive ones")
        print("      to advisors first. It needs calibration against human labels before use.")


def show_stt(turns):
    a = stt_quality_audit(turns)
    if not a.get("turns"):
        print("\n  FEATURE 5 · STT AUDIT — no transcribed turns in this run")
        return
    print(f"\n  FEATURE 5 · SPEECH-TO-TEXT QUALITY AUDIT   ({a['turns']} turns)")
    print(f"      {'locale':10} {'turns':>7} {'mean conf':>10} {'deflect':>9} {'repeat':>8}")
    for loc, d in sorted(a["by_locale"].items(), key=lambda kv: -kv[1]["turns"]):
        print(f"      {loc:10} {d['turns']:>7} {d['mean_confidence']:>10.3f} "
              f"{d['deflection_rate']:>8.1%} {d['repeat_rate']:>7.1%}")
    print(f"\n      {len(a['sample_for_human_transcription'])} lowest-confidence turns sampled "
          f"for human transcription")
    print(f"      {a['note']}")


def show_repo(calls, turns):
    repo = success_repository(calls, turns)
    print(f"\n  FEATURE 6 · SUCCESSFUL CALL REPOSITORY   ({len(repo)} qualifying calls)")
    if not repo:
        print("      none yet - a call qualifies only if it booked, stayed clean on compliance,")
        print("      and did not escalate. A booking won by irritating the customer is not a")
        print("      training example.")
        return
    print(f"      {'call':10} {'product':13} {'loc':5} {'turns':>6} {'secs':>6} "
          f"{'mood':10} {'SR'}")
    for r in repo[:10]:
        print(f"      {(r['correlation_id'] or '')[:8]:10} {r['product']:13} "
              f"{str(r['locale']):5} {r['turns']:>6} {r['bot_seconds']:>6.1f} "
              f"{str(r['sentiment']):10} {r['sr_number']}")


def write_html(path, content, calls, turns):
    cuts = intelligence_cuts(calls)
    f = funnel(calls)
    times = best_time_to_call(calls, "attempt_hour")
    sent = sentiment_trends(calls)
    peak = max((r["connect_rate"] for r in times), default=1) or 1

    def bars(rows):
        out = []
        for r in rows:
            h = int(r["connect_rate"] / peak * 100)
            cls = "bar" + ("" if r["reliable"] else " thin")
            out.append(f'<div class="col"><div class="{cls}" style="height:{h}%" '
                       f'title="{r["attempts"]} attempts"></div>'
                       f'<span>{r["slice"]}</span></div>')
        return "".join(out)

    def table(data, label):
        head = ("<tr><th>" + label + "</th><th>att</th><th>connect</th><th>agree</th>"
                "<th>book</th><th>contain</th></tr>")
        rows = "".join(
            f"<tr><td>{k}</td><td>{d['attempts']}</td>"
            f"<td>{'-' if d['connect_rate'] is None else format(d['connect_rate'], '.1%')}</td>"
            f"<td>{d['agree_rate']:.1%}</td><td>{d['book_rate']:.1%}</td>"
            f"<td>{d['containment']:.1%}</td></tr>"
            for k, d in sorted(data.items(), key=lambda kv: -kv[1]["attempts"]))
        return f"<table>{head}{rows}</table>"

    warn = "" if content.provenance == "blc-approved" else (
        '<p class="warn">Synthetic content · simulated dialer and advisor · uncalibrated '
        'sentiment. The arithmetic is real, the inputs are not. Not for external use.</p>')

    html = f"""<!doctype html><meta charset="utf-8">
<title>Insights — {content.pack_name}</title>
<style>
 body{{font:14px/1.6 system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:24px}}
 h1{{font-size:18px;margin:0 0 4px}} h2{{font-size:12px;text-transform:uppercase;
   letter-spacing:.8px;color:#8b949e;margin:28px 0 10px}}
 .warn{{background:#2a2010;border:1px solid #4a3a12;color:#d29922;padding:9px 13px;
   border-radius:7px;font-size:12px}}
 .grid{{display:flex;gap:10px;flex-wrap:wrap}}
 .card{{background:#161b22;border:1px solid #283039;border-radius:9px;padding:13px 17px;min-width:120px}}
 .card b{{display:block;font-size:22px;font-weight:650}} .card span{{color:#8b949e;font-size:11px}}
 table{{border-collapse:collapse;font-size:13px;margin-bottom:8px}}
 th,td{{border-bottom:1px solid #283039;padding:5px 13px 5px 0;text-align:left}}
 th{{color:#8b949e;font-weight:600;font-size:11px;text-transform:uppercase}}
 .chart{{display:flex;align-items:flex-end;gap:6px;height:150px;
   border-bottom:1px solid #283039;padding-bottom:4px}}
 .col{{display:flex;flex-direction:column;justify-content:flex-end;align-items:center;flex:1}}
 .bar{{width:100%;background:#58a6ff;border-radius:3px 3px 0 0;min-height:2px}}
 .bar.thin{{background:#3a4a5c}} .col span{{font-size:10px;color:#8b949e;margin-top:4px}}
</style>
<h1>Outbound voice agent — insights</h1>
<p style="color:#8b949e;font-size:12px">pack {content.pack_name} @ {content.content_hash}
 · {f['attempted']:,} attempts</p>
{warn}
<h2>Funnel</h2><div class="grid">
 <div class="card"><b>{f['attempted']:,}</b><span>attempted</span></div>
 <div class="card"><b>{f['contacted']:,}</b><span>contacted</span></div>
 <div class="card"><b>{f['contained']:,}</b><span>handled without a human</span></div>
 <div class="card"><b>{f['agreed']:,}</b><span>agreed</span></div>
 <div class="card"><b>{f['booked']:,}</b><span>booked SR</span></div></div>
<h2>Feature 3 — connect rate by hour (pale = thin sample)</h2>
<div class="chart">{bars(times)}</div>
<h2>Feature 2 — sentiment</h2>
<div class="grid">{"".join(f'<div class="card"><b>{n}</b><span>{k}</span></div>' for k, n in sent.get("labels", {}).items()) or '<div class="card"><b>0</b><span>none recorded</span></div>'}</div>
<h2>Feature 4 — intelligence cuts</h2>
{table(cuts.get('product', {}), 'product')}
{table(cuts.get('locale', {}), 'language')}
{table(cuts.get('zone', {}), 'zone')}
<h2>Feature 6 — successful call repository</h2>
<p style="color:#8b949e">{len(success_repository(calls, turns))} calls qualify: booked,
 compliance-clean, non-escalating.</p>
"""
    path.write_text(html, encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--pack", default=None)
    ap.add_argument("--html", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    content = Content(args.pack)
    aud = Audit(args.run)
    calls, turns = aud.read_calls(), aud.read_turns()
    if not calls:
        raise SystemExit(f"no calls in runs/{args.run}/")

    banner(content, calls)
    show_sentiment(calls)
    show_best_time(calls)
    show_cuts(calls)
    show_stt(turns)
    show_repo(calls, turns)

    if args.json:
        payload = {"funnel": funnel(calls), "sentiment": sentiment_trends(calls),
                   "best_time": best_time_to_call(calls), "cuts": intelligence_cuts(calls),
                   "stt": stt_quality_audit(turns),
                   "repository": success_repository(calls, turns)}
        pathlib.Path(args.json).write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                                           encoding="utf-8")
        print(f"\n  json -> {args.json}")

    if args.html:
        p = write_html(pathlib.Path(args.html), content, calls, turns)
        print(f"\n  dashboard -> {p}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
