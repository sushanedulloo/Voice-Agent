"""Charter features 2-6. Everything here reads the audit trail and computes, nothing guesses.

    2  Sentiment analysis            -> engine/sentiment.py, aggregated here as trends
    3  Best time to call             -> connect rate by hour, weekday, zone, product
    4  Intelligence cuts             -> conversion and attempt metrics, sliced
    5  Speech-to-text quality audit  -> sampled confidence + deflection as a proxy for WER
    6  Successful bot call repository-> the calls worth keeping for QA and training

This is why instrumentation went in first. Five of the seven charter capabilities are analytics
over call records; none of them needed new plumbing, because every turn and every disposition
has been written to an append-only log since the first working call.

A NOTE ON WHAT THESE NUMBERS ARE
--------------------------------
Computed from SIMULATED calls against SYNTHETIC content with an UNCALIBRATED sentiment lexicon
and a stand-in router. The arithmetic is real; the inputs are not. Every function here reports
its sample size so a thin slice cannot be mistaken for a finding, and `tools/insights.py` prints
the provenance banner alongside every table.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

NON_TALK = {"NOT_CONTACTED", "ANSWERING_MACHINE"}
TRANSFERS = {"AGREED_TRANSFERRED", "ESCALATED_TRANSFERRED"}

# Below this, a slice is noise. A 100%-connect hour built on three attempts is not a finding,
# and presenting it as one is how analytics loses credibility with an operations team.
MIN_SAMPLE = 30


def _wilson(hits: int, n: int, z: float = 1.96) -> tuple:
    """95% confidence interval on a rate. Wilson, not normal-approx: these are small slices
    with rates near 0, where the normal interval goes negative and looks absurd."""
    if not n:
        return 0.0, 0.0, 0.0
    p = hits / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(p, 4), round(max(0.0, centre - margin), 4), round(min(1.0, centre + margin), 4)


def _contacted(call) -> bool:
    return call.get("disposition") not in NON_TALK


def _booked(call) -> bool:
    return bool((call.get("advisor") or {}).get("sr_number"))


# ---------------------------------------------------------------- feature 3
def best_time_to_call(calls: list, by: str = "attempt_hour") -> list:
    """Connect rate per slice, with a confidence interval and a sample count.

    "Optimise calling windows based on historical metadata to improve connect rates" - CH-S4 #3.

    Returns every slice, including the under-sampled ones, flagged rather than hidden. An
    operations team deciding when to dial needs to see that 14:00 has forty attempts behind it
    and 09:00 has four.
    """
    buckets = defaultdict(lambda: [0, 0])          # key -> [attempts, connects]
    for c in calls:
        key = c.get(by)
        if key is None:
            continue
        buckets[key][0] += 1
        buckets[key][1] += _contacted(c)

    rows = []
    for key, (attempts, connects) in sorted(buckets.items()):
        rate, lo, hi = _wilson(connects, attempts)
        rows.append({"slice": key, "attempts": attempts, "connects": connects,
                     "connect_rate": rate, "ci_low": lo, "ci_high": hi,
                     "reliable": attempts >= MIN_SAMPLE})
    return rows


def recommended_windows(calls: list, top: int = 3) -> list:
    """The hours worth dialling, ranked by the LOWER confidence bound rather than the point
    estimate - so a lucky small sample cannot beat a solid large one."""
    rows = [r for r in best_time_to_call(calls) if r["reliable"]]
    return sorted(rows, key=lambda r: -r["ci_low"])[:top]


# ---------------------------------------------------------------- feature 4
def intelligence_cuts(calls: list) -> dict:
    """Conversion and attempt metrics sliced by the dimensions the base actually carries.

    "Visual data reporting and dashboards tracking conversion metrics and contact attempts"
    - CH-S4 #4.
    """
    # An answered call carries `language_used` (from the handoff payload); an unanswered
    # attempt carries `locale` (from the dialer). Slicing on one name silently dropped the
    # other half and every locale row read 0%.
    ALIAS = {"locale": ("language_used", "locale")}

    def slice_by(field):
        out = {}
        for c in calls:
            key = next((c[k] for k in ALIAS.get(field, (field,))
                        if c.get(k) not in (None, "")), None)
            if key in (None, ""):
                continue
            d = out.setdefault(key, {"attempts": 0, "contacted": 0, "agreed": 0,
                                     "transferred": 0, "booked": 0, "bot_seconds": 0})
            d["attempts"] += 1
            d["contacted"] += _contacted(c)
            d["agreed"] += c.get("disposition") == "AGREED_TRANSFERRED"
            d["transferred"] += c.get("disposition") in TRANSFERS
            d["booked"] += _booked(c)
            d["bot_seconds"] += (c.get("bot_duration_ms") or 0) / 1000
        for d in out.values():
            d["connect_rate"] = round(d["contacted"] / d["attempts"], 4) if d["attempts"] else 0
            d["agree_rate"] = round(d["agreed"] / d["contacted"], 4) if d["contacted"] else 0
            d["book_rate"] = round(d["booked"] / d["contacted"], 4) if d["contacted"] else 0
            d["containment"] = round(1 - d["transferred"] / d["contacted"], 4) if d["contacted"] else 0
            d["bot_minutes"] = round(d["bot_seconds"] / 60, 1)
        return out

    cuts = {field: slice_by(field)
            for field in ("product", "locale", "zone", "attempt_hour", "persona_tier")}
    # persona_tier exists only on answered calls, so its connect rate is 100% by construction.
    # Reporting it would be a lie of omission - blank it rather than print a meaningless 100%.
    for d in cuts["persona_tier"].values():
        d["connect_rate"] = None
    return cuts


def funnel(calls: list) -> dict:
    disp = Counter(c.get("disposition") for c in calls)
    contacted = sum(1 for c in calls if _contacted(c))
    transferred = sum(1 for c in calls if c.get("disposition") in TRANSFERS)
    return {
        "attempted": len(calls),
        "contacted": contacted,
        "contained": contacted - transferred,
        "transferred": transferred,
        "agreed": disp.get("AGREED_TRANSFERRED", 0),
        "escalated": disp.get("ESCALATED_TRANSFERRED", 0),
        "booked": sum(1 for c in calls if _booked(c)),
        "dispositions": dict(disp.most_common()),
    }


# ---------------------------------------------------------------- feature 2 (trends)
def sentiment_trends(calls: list) -> dict:
    """Sentiment as a trend, which is what the charter asked for - not per-call labels."""
    labels, escalating, by_product = Counter(), 0, defaultdict(Counter)
    booked_by_label, total_by_label = Counter(), Counter()
    for c in calls:
        s = c.get("sentiment") or {}
        label = s.get("label")
        if not label:
            continue
        labels[label] += 1
        escalating += bool(s.get("escalating"))
        by_product[c.get("product")][label] += 1
        total_by_label[label] += 1
        booked_by_label[label] += _booked(c)

    conversion = {lbl: round(booked_by_label[lbl] / n, 4)
                  for lbl, n in total_by_label.items() if n >= MIN_SAMPLE}
    return {"labels": dict(labels.most_common()),
            "escalating_calls": escalating,
            "by_product": {k: dict(v) for k, v in by_product.items()},
            "booking_rate_by_sentiment": conversion,
            "calibrated": False}


# ---------------------------------------------------------------- feature 5
def stt_quality_audit(turns: list, sample_rate: float = 0.05) -> dict:
    """Proxy metrics for transcription quality, pending real WER.

    "Evaluates transcription accuracy and manages a secure, 3-year storage archive" - CH-S4 #5.

    HONEST LIMITATION: real WER needs a human-transcribed reference, and we have none. What is
    computable from the log is the shape of ASR trouble: low router confidence, out-of-scope
    deflection and repeat requests all spike when transcription degrades. They are LEADING
    INDICATORS, not accuracy - reported as such, and the sampled set is what a human then
    transcribes to produce the real number (FR-703).
    """
    heard = [t for t in turns if t.get("heard")]
    if not heard:
        return {"turns": 0}

    by_locale = defaultdict(lambda: {"turns": 0, "deflected": 0, "low_conf": 0,
                                     "repeats": 0, "conf_sum": 0.0})
    for t in heard:
        d = by_locale[t.get("locale", "?")]
        d["turns"] += 1
        d["deflected"] += t.get("route_kind") == "out_of_scope"
        d["low_conf"] += (t.get("band") == "deflect")
        d["repeats"] += t.get("route_id") == "REPEAT"
        d["conf_sum"] += t.get("confidence") or 0.0

    for d in by_locale.values():
        n = d["turns"]
        d["mean_confidence"] = round(d["conf_sum"] / n, 3)
        d["deflection_rate"] = round(d["deflected"] / n, 4)
        d["repeat_rate"] = round(d["repeats"] / n, 4)
        d.pop("conf_sum")

    # deterministic sample for human transcription - lowest confidence first, since that is
    # where transcription errors concentrate and where a human hour buys the most information
    ranked = sorted(heard, key=lambda t: t.get("confidence") or 0.0)
    take = max(1, int(len(heard) * sample_rate))
    sample = [{"correlation_id": t["correlation_id"], "turn": t["turn"],
               "locale": t.get("locale"), "heard": t["heard"],
               "confidence": t.get("confidence"), "route": t.get("route_id")}
              for t in ranked[:take]]

    return {"turns": len(heard), "by_locale": {k: dict(v) for k, v in by_locale.items()},
            "sample_for_human_transcription": sample,
            "note": "proxy indicators, not WER - real accuracy requires human references"}


# ---------------------------------------------------------------- feature 6
def success_repository(calls: list, turns: list, limit: int = 50) -> list:
    """Calls worth keeping for QA, compliance and training.

    "Archiving successful automated interactions for quality assurance, compliance, and
    training" - CH-S4 #6.

    A "successful" call is not simply one that booked. It is one a QA reviewer can learn from:
    it reached a booking, it stayed clean on compliance, and it did so without escalating. A
    booked call that annoyed the customer into agreeing is the opposite of a training example.
    """
    by_call = defaultdict(list)
    for t in turns:
        by_call[t["correlation_id"]].append(t)

    out = []
    for c in calls:
        if not _booked(c):
            continue
        s = c.get("sentiment") or {}
        if s.get("escalating"):
            continue
        if c.get("escalation_flags"):
            continue
        rows = by_call.get(c.get("correlation_id"), [])
        out.append({
            "correlation_id": c.get("correlation_id"),
            "product": c.get("product"),
            "locale": c.get("language_used"),
            "turns": c.get("turn_count"),
            "bot_seconds": round((c.get("bot_duration_ms") or 0) / 1000, 1),
            "sentiment": s.get("label"),
            "agreement_confidence": c.get("agreement_confidence"),
            "disclosures": c.get("disclosures_played"),
            "content_hash": c.get("content_hash") or (rows[0].get("content_hash") if rows else None),
            "sr_number": (c.get("advisor") or {}).get("sr_number"),
            # ids, not text - the words are reconstructable from the pack at content_hash
            "path": c.get("nodes_played"),
        })

    # shortest clean bookings first: the efficient calls are the ones worth teaching
    return sorted(out, key=lambda r: (r["turns"], r["bot_seconds"]))[:limit]
