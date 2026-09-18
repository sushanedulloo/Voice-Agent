#!/usr/bin/env python3
"""Run a campaign end to end: base file in, booked SRs and a cost report out.

    python tools/make_base.py --rows 2000
    python apps/campaign.py --base runs/base.csv --concurrency 243
    python apps/campaign.py --base runs/base.csv --pack packs/sbic-blc-2026-10

This is the whole loop, with the parts we do not own simulated and labelled:

    base file (masked, no PII)
      -> dialer      predictive/progressive, connect rate, AMD      [partner's - simulated]
      -> BOT         pitch, probe, detect agreement, dispose        [OURS - real]
      -> transfer    handoff payload across our boundary            [OURS - real]
      -> advisor     verify, IVR or C2B, raise SR                   [partner's - simulated]
      -> audit       append-only turns.jsonl + calls.jsonl          [OURS - real]
      -> report      cost per booked SR vs the human control arm    [OURS - real]

Concurrency defaults to 243 because that is the modelled Phase-1 peak (~121 average). The
number worth watching is not throughput, it is whether per-turn engine latency degrades as
sessions pile up - a router that is 2 ms alone and 80 ms at peak has no budget left for the
network.
"""

import argparse
import csv
import pathlib
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from engine import Content, Session                              # noqa: E402
from engine import advisor, persona                              # noqa: E402
from engine.audit import Audit                                   # noqa: E402
from engine.machine import ComplianceError                       # noqa: E402

# Dialer-side assumptions. Not ours, not verified. CH-* step 8-9.
CONNECT_RATE = 0.42          # answered, of attempted
AMD_MACHINE_RATE = 0.19      # of answered, an answering machine picked up

# TCCCPR permits promotional calls 09:00-21:00. Connect rates are NOT flat across that window -
# nobody answers a sales call at 10am on a weekday and everybody does at 7pm. Feature 3 of the
# charter ("optimise calling windows based on historical metadata") exists because that curve is
# worth money, and it cannot be measured unless attempts carry the hour they were placed.
#
# The shape below is a GUESS. Replacing it with the partner's actual connect-by-hour data is
# item one of any best-time-to-call work - see tools/insights.py.
CALL_WINDOW = range(9, 21)
HOUR_CONNECT_MULTIPLIER = {9: 0.72, 10: 0.81, 11: 0.88, 12: 0.79, 13: 0.62, 14: 0.85,
                           15: 0.94, 16: 0.98, 17: 1.06, 18: 1.19, 19: 1.27, 20: 1.09}
DAY_CONNECT_MULTIPLIER = {0: 0.94, 1: 1.0, 2: 1.02, 3: 1.0, 4: 0.97, 5: 1.11, 6: 0.86}
NON_CONTACT = "NOT_CONTACTED"
ANSWERING_MACHINE = "ANSWERING_MACHINE"


def run_one(record, content, aud, seed):
    rng = random.Random(seed)
    product, locale = record["product"], record["locale"]
    campaign = {k: v for k, v in record.items()
                if k not in ("masked_ref_id", "product", "locale") and v != ""}
    for key in ("tenure_months", "offer_valid_days", "min_txn_amt", "eligible_amount",
                "processing_fee", "indicative_emi", "current_limit", "enhanced_limit",
                "joining_fee", "annual_fee"):
        if key in campaign:
            campaign[key] = int(campaign[key])

    hour = rng.choice(list(CALL_WINDOW))
    weekday = rng.randrange(7)
    effective = (CONNECT_RATE * HOUR_CONNECT_MULTIPLIER[hour]
                 * DAY_CONNECT_MULTIPLIER[weekday])
    when = {"attempt_hour": hour, "attempt_weekday": weekday, "zone": record.get("zone", "")}

    def unanswered(disposition, ms):
        # An attempt that never connected is still an attempt. It carries no conversation, so
        # it gets a skeletal row - but it MUST be in the log, or connect rate is 100% by
        # construction and best-time-to-call has nothing to measure.
        row = {"disposition": disposition, "product": product, "locale": locale,
               "masked_ref_id": record["masked_ref_id"], "bot_duration_ms": ms,
               "turn_count": 0, "nodes_played": [], "disclosures_played": [],
               "advisor": None, **when}
        aud.call(row, None, {"attempt_only": True})
        return row

    if rng.random() > effective:
        return unanswered(NON_CONTACT, 0)
    if rng.random() < AMD_MACHINE_RATE:
        return unanswered(ANSWERING_MACHINE, 2000)

    session = Session(content, product, campaign, locale=locale,
                      masked_ref_id=record["masked_ref_id"], campaign_id="SIM")
    who = persona.make(product, rng)

    rec = session.start()
    aud.turn(session.correlation_id, content.content_hash, rec, product, locale)

    while not session.finished:
        said = who.reply(session.machine.current, session.machine.listening)
        if said is None:
            session.machine.hang_up()
            break
        try:
            rec = session.say(said)
        except ComplianceError:
            raise
        except RuntimeError:
            session.machine.hang_up()
            break
        aud.turn(session.correlation_id, content.content_hash, rec, product, locale)

    payload = session.handoff_payload()
    outcome = advisor.handle(payload, rng)
    inbound = advisor.to_inbound(outcome) if outcome else None
    aud.call(payload, inbound, {"persona_tier": who.tier, "persona_outcome": who.outcome,
                                **when})
    return {**payload, "advisor": inbound, **when}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="runs/base.csv")
    ap.add_argument("--pack", default=None)
    ap.add_argument("--concurrency", type=int, default=243)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--run-id", default=None)
    args = ap.parse_args()

    content = Content(args.pack)
    if content.provenance != "blc-approved":
        print(f"!! content pack '{content.pack_name}' is {content.provenance.upper()}, "
              f"not BLC-approved. Results are structural only.\n")

    with open(args.base, newline="", encoding="utf-8") as fh:
        records = list(csv.DictReader(fh))
    if args.limit:
        records = records[:args.limit]

    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    aud = Audit(run_id, append_ok=False)
    aud.run_header({"base": args.base, "records": len(records),
                    "concurrency": args.concurrency,
                    "content": content.describe(),
                    "dialer_assumptions": {"connect_rate": CONNECT_RATE,
                                           "amd_machine_rate": AMD_MACHINE_RATE},
                    "advisor_assumptions": advisor.assumptions()})

    print(f"run {run_id} · {len(records)} records · concurrency {args.concurrency} · "
          f"pack {content.pack_name} @ {content.content_hash}")

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(
            lambda pair: run_one(pair[1], content, aud, args.seed + pair[0]),
            enumerate(records)))
    elapsed = time.perf_counter() - started

    dispositions = Counter(r["disposition"] for r in results)
    booked = sum(1 for r in results if (r.get("advisor") or {}).get("sr_number"))
    transferred = sum(1 for r in results
                      if r["disposition"] in ("AGREED_TRANSFERRED", "ESCALATED_TRANSFERRED"))
    agreed = dispositions.get("AGREED_TRANSFERRED", 0)
    contacted = len(results) - dispositions.get(NON_CONTACT, 0) - \
        dispositions.get(ANSWERING_MACHINE, 0)

    print(f"\n  {len(records)} attempted in {elapsed:.1f}s "
          f"({len(records) / elapsed:,.0f} calls/s simulated)\n")
    for name, count in dispositions.most_common():
        print(f"    {name:24} {count:6}  {count / len(results):6.1%}")

    print(f"\n    contacted                {contacted:6}")
    print(f"    agreed (bot)             {agreed:6}  "
          f"{agreed / contacted:6.1%} of contacted")
    print(f"    transferred to advisor   {transferred:6}")
    print(f"    booked SR                {booked:6}  "
          f"{booked / contacted:6.1%} of contacted")
    print(f"\n  audit: runs/{run_id}/  (turns.jsonl, calls.jsonl)")
    print(f"  report: python tools/report.py --run {run_id}")


if __name__ == "__main__":
    main()
