#!/usr/bin/env python3
"""Turn a run's audit trail into the number the engagement is judged on.

    python tools/report.py --run demo2

Two things, and the second is the one that matters:

  1. Script adherence      did the bot say only approved things, in the required order
  2. Cost per booked SR    bot arm against the human control arm, same funnel, same period

Constants come from cost_model.py so there is exactly one place an assumption lives. Every
assumption used is printed with the result, because a cost-per-SR figure without its
assumptions beside it is not defensible and this deal is decided by people who will ask.

CONTAINMENT is computed first and reported first. It is the whole product. A bot that
disqualifies nobody does not save a rupee - it inserts a delay in front of an advisor and then
hands over the same call, having consumed extra telephony minutes to do it. At that point the
correct engineering answer is to turn it off, and a report that cannot say so is decoration.
"""

import argparse
import pathlib
import statistics
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import cost_model as cm                                          # noqa: E402
from engine import Content                                       # noqa: E402
from engine.audit import Audit                                   # noqa: E402

NON_TALK = {"NOT_CONTACTED", "ANSWERING_MACHINE"}
TRANSFERS = {"AGREED_TRANSFERRED", "ESCALATED_TRANSFERRED"}


def adherence(turns, content):
    """RESEARCH 2.6 targets: required-line delivery >=99%, disclosure-before-restricted-topic
    >=98%, identity-before-disclosure 100%, evaluated on EVERY call, not sampled."""
    by_call = {}
    for row in turns:
        by_call.setdefault(row["correlation_id"], []).append(row)

    approved_ids = set(content.faq) | set(content.disclosures)
    for product in content.products.values():
        approved_ids |= set(product.nodes)

    unapproved = 0
    identity_first = ordered = pitched = 0
    for _, rows in by_call.items():
        spoken = [(kind, ident) for r in rows for kind, ident in r["spoke"]]
        unapproved += sum(1 for _, ident in spoken if ident not in approved_ids)
        discl = [ident for kind, ident in spoken if kind == "disclosure"]
        if discl:
            identity_first += discl[0] == "D01_IDENTITY"
        nodes = [ident for kind, ident in spoken if kind == "node"]
        pitch_at = next((i for i, n in enumerate(nodes) if n.startswith("N04")), None)
        if pitch_at is not None:
            pitched += 1
            played_before = {i for kind, i in spoken[:spoken.index(("node", nodes[pitch_at]))]
                             if kind == "disclosure"}
            ordered += {"D01_IDENTITY", "D02_RECORDED_LINE"} <= played_before

    calls_with_disclosure = sum(1 for rows in by_call.values()
                                if any(k == "disclosure" for r in rows for k, _ in r["spoke"]))
    return {
        "calls": len(by_call),
        "unapproved_utterances": unapproved,
        "identity_before_disclosure": identity_first / max(calls_with_disclosure, 1),
        "disclosure_before_pitch": ordered / max(pitched, 1),
        "pitched": pitched,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--pack", default=None)
    args = ap.parse_args()

    content = Content(args.pack)
    aud = Audit(args.run)
    calls, turns = aud.read_calls(), aud.read_turns()
    if not calls:
        raise SystemExit(f"no calls in runs/{args.run}/")

    attempted = len(calls)
    disp = Counter(c["disposition"] for c in calls)
    contacted = sum(1 for c in calls if c["disposition"] not in NON_TALK)
    transferred = sum(1 for c in calls if c["disposition"] in TRANSFERS)
    agreed = disp.get("AGREED_TRANSFERRED", 0)
    booked = sum(1 for c in calls if (c.get("advisor") or {}).get("sr_number"))
    contained = contacted - transferred

    print(f"\n{'=' * 74}\n  RUN {args.run}   pack {content.pack_name} "
          f"@ {content.content_hash} ({content.provenance})\n{'=' * 74}")
    if content.provenance != "blc-approved":
        print("  Content is SYNTHETIC. Adherence below measures the machinery, not the script.")

    # ---- 1. containment ---------------------------------------------------
    print(f"\n  CONTAINMENT  (the product)")
    print(f"    contacted                  {contacted:7}")
    print(f"    handled without a human    {contained:7}   {contained / contacted:6.1%}")
    print(f"    handed to an advisor       {transferred:7}   {transferred / contacted:6.1%}")
    print(f"      of which agreed          {agreed:7}")
    print(f"      of which escalated       {disp.get('ESCALATED_TRANSFERRED', 0):7}"
          f"   <- consumed an advisor, was not a sale")

    # ---- 2. adherence ------------------------------------------------------
    adh = adherence(turns, content)
    print(f"\n  SCRIPT ADHERENCE  ({adh['calls']} calls, every call scored, none sampled)")
    print(f"    unapproved utterances      {adh['unapproved_utterances']:7}"
          f"   target 0")
    print(f"    identity before disclosure {adh['identity_before_disclosure']:7.1%}"
          f"   target 100%")
    print(f"    disclosure before pitch    {adh['disclosure_before_pitch']:7.1%}"
          f"   target >=98%   (of {adh['pitched']} calls that reached a pitch)")
    if not adh["pitched"]:
        print("      no call reached a pitch node - the number above measures nothing")

    # ---- 3. latency --------------------------------------------------------
    engine_ms = [r["router_ms"] + r["policy_ms"] for r in turns if r["heard"] is not None]
    if engine_ms:
        engine_ms.sort()
        p95 = engine_ms[int(len(engine_ms) * 0.95)]
        print(f"\n  ENGINE LATENCY  (our share only - no ASR, no TTS, no network)")
        print(f"    p50 {statistics.median(engine_ms):6.2f} ms    p95 {p95:6.2f} ms"
              f"    max {engine_ms[-1]:6.2f} ms   at concurrency, {len(engine_ms)} turns")
        print(f"    budget NFR-101: P50 <= 1000 ms, P95 <= 1800 ms end to end")

    # ---- 4. economics ------------------------------------------------------
    bot_cost_per_conv, _direct = cm.loaded_cost("B", cm.CONVERSATIONS_PER_MO)
    advisor_ms = [(c.get("advisor") or {}).get("advisor_handle_time_ms") or 0 for c in calls]
    advisor_minutes = sum(advisor_ms) / 60000

    print(f"\n  COST PER BOOKED SR")
    print(f"    booked SRs                 {booked:7}")
    if booked:
        for seat in (cm.SEAT_COST_LOW, cm.SEAT_COST_HIGH):
            per_min = cm.human_cost_per_minute(seat)
            bot_arm = (contacted * bot_cost_per_conv + advisor_minutes * per_min) / booked
            human_pitch_min = cm.HUMAN_PITCH_SEC / 60
            human_arm = cm.cost_per_agreement(
                per_min * human_pitch_min, cm.AGREE_RATE_HUMAN) / cm.CONSENT_TO_BOOKING
            delta = (bot_arm - human_arm) / human_arm
            print(f"    seat Rs {seat:,}/mo  ->  bot arm Rs {bot_arm:7.2f}"
                  f"   human arm Rs {human_arm:7.2f}   {delta:+6.1%}")
    else:
        print("    no SRs booked - no cost per SR to compute")

    print(f"\n  ASSUMPTIONS USED (none verified with the client)")
    print(f"    bot cost/conversation Rs {bot_cost_per_conv:.2f} at "
          f"{cm.lakh(cm.CONVERSATIONS_PER_MO):.1f} lakh conv/mo (config B, loaded)")
    print(f"    seat utilisation {cm.TALK_UTILISATION:.0%} · human agree rate "
          f"{cm.AGREE_RATE_HUMAN:.0%} · consent-to-booking {cm.CONSENT_TO_BOOKING:.0%}")
    print(f"    advisor minutes consumed by this run: {advisor_minutes:,.0f}")

    # ---- verdict -----------------------------------------------------------
    print(f"\n{'-' * 74}")
    if contained / contacted < 0.50:
        print(f"  VERDICT: containment {contained / contacted:.1%}. The bot is handing most of")
        print( "  its calls to a human anyway, so it is adding a step and a telephony leg")
        print( "  rather than removing cost. Fix the router before quoting any economics.")
    elif adh["unapproved_utterances"]:
        print("  VERDICT: an unapproved utterance was played. Nothing else in this report")
        print("  matters until that is zero.")
    else:
        print(f"  VERDICT: containment {contained / contacted:.1%}, adherence clean.")
    print(f"{'-' * 74}\n")


if __name__ == "__main__":
    main()
