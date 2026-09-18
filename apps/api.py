#!/usr/bin/env python3
"""The production service. Implements docs/api/openapi.yaml.

    python apps/api.py                     # http://localhost:8078, /docs for Swagger

This is the surface the calling partner integrates against. apps/server.py is the demo console;
this is the product. The difference matters: a console proves the dialogue works, an API is what
somebody else's dialer, CRM and MIS pipeline actually call at three in the morning.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
It does not dial. It does not originate. ADR-003 keeps us a media endpoint the partner INVITEs
into, because originating calls would make us the sender under TCCCPR - DLT registration,
140-series CLI, DNCR scrubbing, abandoned-call ratios, penalties to Rs 10 lakh per violation.
That perimeter belongs to the Principal Entity. There is no endpoint here that starts a call,
and that absence is a design decision, not an omission.

AUTH
----
Bearer token from OUTBOUND_API_TOKEN. Deliberately crude: the real deployment terminates auth
at the partner's gateway with mTLS, and a token check here is the belt to that gateway's braces.
It is NOT the security model - it exists so the service is never accidentally open, which is the
failure mode that actually happens.
"""

import hashlib
import json
import os
import pathlib
import sys
import time
from datetime import date, datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import uvicorn                                                    # noqa: E402
from fastapi import Depends, FastAPI, HTTPException, Header       # noqa: E402
from fastapi.responses import JSONResponse                        # noqa: E402

import cost_model as cm                                           # noqa: E402
from engine import Content                                        # noqa: E402
from engine.audit import Audit, DEFAULT_DIR                       # noqa: E402
from engine.prerender import INDEX_NAME, WAV_CACHE                # noqa: E402
from engine.insights import funnel, intelligence_cuts             # noqa: E402

STARTED = time.time()
TOKEN = os.environ.get("OUTBOUND_API_TOKEN", "")
PACK = os.environ.get("OUTBOUND_CONTENT_PACK") or None

app = FastAPI(title="SBI Card AI-BOT Voice Agent",
              version="0.1.0",
              description="Interface contracts per docs/api/openapi.yaml. "
                          "This service never originates a call (ADR-003).")

CONTENT = Content(PACK)
CAMPAIGNS: dict = {}          # in-memory. Production: the partner's store, not ours.


def auth(authorization: str = Header(default="")):
    """Refuse to run open. If no token is configured we still require the header to be absent
    deliberately rather than by accident - an unset token in production is the bug."""
    if not TOKEN:
        return                                  # explicit dev mode; /ready reports it
    if authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="invalid or missing bearer token")


def _iso(ts=None):
    return (ts or datetime.now(timezone.utc)).isoformat(timespec="seconds")


def _runs():
    d = pathlib.Path(DEFAULT_DIR)
    return sorted([p.name for p in d.iterdir() if (p / "calls.jsonl").exists()]) if d.exists() else []


def _find_call(call_id: str):
    """Locate a call across runs. Production reads one store; the run split is a local artefact."""
    for run in reversed(_runs()):
        aud = Audit(run)
        for c in aud.read_calls():
            if c.get("correlation_id") == call_id or c.get("masked_ref_id") == call_id:
                turns = [t for t in aud.read_turns() if t["correlation_id"] == c["correlation_id"]]
                return run, c, turns
    return None, None, None


# ---------------------------------------------------------------- health
@app.get("/health", tags=["ops"])
def health():
    """Liveness. Deliberately dependency-free: if this needs the content pack to answer, a bad
    pack takes the service out of the load balancer and you lose the ability to diagnose it."""
    return {"status": "ok", "uptime_seconds": round(time.time() - STARTED, 1)}


@app.get("/ready", tags=["ops"])
def ready():
    """Readiness. Fails closed on anything that would make a call go wrong rather than slow."""
    checks = {
        "content_pack": bool(CONTENT.products),
        "auth_configured": bool(TOKEN),
        "audio_index": (WAV_CACHE / INDEX_NAME).exists(),
    }
    body = {
        "ready": checks["content_pack"],
        "checks": checks,
        "pack": CONTENT.describe(),
        # A pack that is not BLC-approved must be impossible to mistake for one that is.
        "provenance_warning": (None if CONTENT.provenance == "blc-approved"
                               else f"content is {CONTENT.provenance}, NOT approved for live calls"),
    }
    return JSONResponse(body, status_code=200 if body["ready"] else 503)


# ---------------------------------------------------------------- campaigns
@app.post("/campaigns", tags=["campaign"], dependencies=[Depends(auth)])
def create_campaign(body: dict):
    for field in ("product_code", "campaign_date", "script_version", "glossary_version"):
        if not body.get(field):
            raise HTTPException(422, f"{field} is required")
    if body["product_code"] not in CONTENT.products:
        raise HTTPException(422, f"unknown product_code {body['product_code']!r}")

    cid = hashlib.sha256(
        f"{body['product_code']}{body['campaign_date']}{time.time()}".encode()).hexdigest()[:16]
    CAMPAIGNS[cid] = {**body, "campaign_id": cid, "created_at": _iso(),
                      "content_hash": CONTENT.content_hash, "records": 0,
                      "status": "registered"}
    return CAMPAIGNS[cid]


@app.post("/campaigns/{campaign_id}/records", tags=["campaign"], dependencies=[Depends(auth)])
def load_records(campaign_id: str, body: dict):
    """Accept a batch of calling records.

    Constraint 3 is enforced here, at the boundary, not documented and hoped for. A record
    carrying anything PII-shaped is REJECTED - the whole batch - rather than accepted and
    stripped. Silently cleaning a payload teaches the sender that sending PII is fine.
    """
    campaign = CAMPAIGNS.get(campaign_id)
    if not campaign:
        raise HTTPException(404, "unknown campaign")

    records = body.get("records") or []
    declared = set(CONTENT.vars["slots"])
    forbidden = {"name", "full_name", "mobile", "phone", "email", "dob", "date_of_birth",
                 "address", "pincode", "pin_code", "card_number", "pan", "aadhaar"}

    problems = []
    for i, r in enumerate(records):
        if not r.get("masked_ref_id"):
            problems.append(f"record {i}: masked_ref_id is required")
        offered = set((r.get("offer_variables") or {}))
        bad = offered & forbidden
        if bad:
            problems.append(f"record {i}: PII-shaped fields rejected: {sorted(bad)}")
        unknown = offered - declared
        if unknown:
            problems.append(f"record {i}: undeclared offer variables {sorted(unknown)}")
    if problems:
        raise HTTPException(422, {"accepted": 0, "errors": problems[:20]})

    campaign["records"] += len(records)
    campaign["status"] = "loaded"
    return {"campaign_id": campaign_id, "accepted": len(records),
            "total_records": campaign["records"]}


# ---------------------------------------------------------------- calls
@app.get("/calls/{call_id}", tags=["calls"], dependencies=[Depends(auth)])
def get_call(call_id: str):
    run, call, turns = _find_call(call_id)
    if not call:
        raise HTTPException(404, "unknown call")
    return {
        "call_id": call.get("correlation_id"),
        "run": run,
        "masked_ref_id": call.get("masked_ref_id"),
        "product": call.get("product"),
        "language_used": call.get("language_used"),
        "disposition": call.get("disposition"),
        "bot_duration_ms": call.get("bot_duration_ms"),
        "content_hash": call.get("content_hash"),
        "sentiment": call.get("sentiment"),
        "advisor": call.get("advisor"),
        "turns": [{"turn": t["turn"], "heard": t["heard"], "route": t.get("route_id"),
                   "confidence": t.get("confidence"), "band": t.get("band"),
                   "node_before": t.get("node_before"), "node_after": t.get("node_after"),
                   "spoke": t.get("spoke"), "ts": t.get("ts")} for t in turns],
    }


@app.get("/calls/{call_id}/evidence", tags=["calls"], dependencies=[Depends(auth)])
def evidence(call_id: str):
    """The compliance evidence packet. CR-103, constraint 5.

    This is the artefact a regulator or an internal auditor reads. It answers, for ONE call:
    which approved content version spoke, which disclosures played and in what order, whether
    any line was cut short by barge-in, and whether anything unapproved was ever uttered.

    Utterance IDS, not text. The words are reconstructable from the pack at content_hash, and
    storing them twice creates two things to keep in sync and two things to redact.
    """
    run, call, turns = _find_call(call_id)
    if not call:
        raise HTTPException(404, "unknown call")

    approved = set(CONTENT.faq) | set(CONTENT.disclosures)
    for p in CONTENT.products.values():
        approved |= set(p.nodes)
    spoken = [(k, i) for t in turns for k, i in (t.get("spoke") or [])]
    unapproved = [i for k, i in spoken if not i.startswith("BC_") and i not in approved]

    disclosures = call.get("disclosures_played") or []
    pitched = any(i.startswith("N04") for _, i in spoken)
    identity_first = disclosures[:1] == ["D01_IDENTITY"] if disclosures else False

    rules = [
        {"rule": "identity_before_disclosure", "target": "100%",
         "pass": identity_first or not disclosures},
        {"rule": "disclosure_before_pitch", "target": ">=98%",
         "pass": (not pitched) or {"D01_IDENTITY", "D02_RECORDED_LINE"} <= set(disclosures)},
        {"rule": "no_unapproved_utterance", "target": "0",
         "pass": not unapproved, "detail": unapproved[:5]},
        {"rule": "agreement_requires_terms", "target": "100%",
         "pass": call.get("disposition") != "AGREED_TRANSFERRED"
                 or any(d.endswith("_TERMS") for d in disclosures)},
    ]
    failed = [r["rule"] for r in rules if not r["pass"]]

    return {
        "call_id": call.get("correlation_id"),
        "correlation_id": call.get("correlation_id"),
        "script_version": call.get("content_version"),
        "glossary_version": call.get("content_version"),
        "evaluator_version": "rules-0.1.0",
        "content_hash": call.get("content_hash"),
        # We point at the partner's recording; we never hold a copy (constraint 3, ADR-003).
        "audio_uri": call.get("recording_pointer"),
        "disclosures_played": disclosures,
        "truncated_utterances": call.get("truncated_utterances") or [],
        "rule_results": rules,
        "safety_tagged": bool(failed) or bool(call.get("escalation_flags")),
        "failed_rules": failed,
        "reviewer_decision": None,          # set by a human; never inferred
    }


# ---------------------------------------------------------------- reports
@app.get("/reports/daily", tags=["reports"], dependencies=[Depends(auth)])
def daily(run: str = "", report_date: str = ""):
    runs = [run] if run else _runs()
    if not runs:
        raise HTTPException(404, "no runs available")
    calls = [c for r in runs for c in Audit(r).read_calls()]
    if not calls:
        raise HTTPException(404, "no calls in the selected runs")

    f = funnel(calls)
    talk = [c.get("bot_duration_ms") or 0 for c in calls if c.get("turn_count")]
    disqualified = [c.get("bot_duration_ms") or 0 for c in calls
                    if c.get("disposition") == "NOT_INTERESTED"]
    cuts = intelligence_cuts(calls)

    return {
        "date": report_date or date.today().isoformat(),
        "runs": runs,
        "attempts": f["attempted"],
        "connects": f["contacted"],
        "bot_handled": f["contained"],
        "transferred": f["transferred"],
        "disposed_not_interested": f["dispositions"].get("NOT_INTERESTED", 0),
        "dnc_requests": f["dispositions"].get("DNC_REQUESTED", 0),
        "mean_talk_seconds": round(sum(talk) / len(talk) / 1000, 1) if talk else 0,
        # The number the whole design optimises for. ~88% of contacts end in a no, and the
        # saving is in reaching that no quickly.
        "mean_time_to_disqualify_seconds": (round(sum(disqualified) / len(disqualified) / 1000, 1)
                                            if disqualified else 0),
        "by_language": {k: {"attempts": v["attempts"], "connects": v["contacted"],
                            "booked": v["booked"]} for k, v in cuts["locale"].items()},
        "content_provenance": CONTENT.provenance,
    }


@app.get("/reports/funnel", tags=["reports"], dependencies=[Depends(auth)])
def funnel_report(run: str = "", seat_cost_inr: int = 0):
    """Both arms. A bot number with no human number beside it is not a result."""
    runs = [run] if run else _runs()
    calls = [c for r in runs for c in Audit(r).read_calls()]
    if not calls:
        raise HTTPException(404, "no calls")

    f = funnel(calls)
    seat = seat_cost_inr or cm.SEAT_COST_LOW
    per_min = cm.human_cost_per_minute(seat)
    bot_cost, _ = cm.loaded_cost("B", cm.CONVERSATIONS_PER_MO)
    advisor_min = sum((c.get("advisor") or {}).get("advisor_handle_time_ms") or 0
                      for c in calls) / 60000

    contacts, agreements, booked = f["contacted"], f["agreed"], f["booked"]
    bot_total = contacts * bot_cost + advisor_min * per_min
    human_pitch_min = cm.HUMAN_PITCH_SEC / 60

    def safe(n, d):
        return round(n / d, 2) if d else None

    return {
        "runs": runs,
        "arms": [
            {"arm": "bot", "contacts": contacts, "agreements": agreements,
             "booked_srs": booked,
             "cost_per_contact_inr": safe(bot_total, contacts),
             "cost_per_agreement_inr": safe(bot_total, agreements),
             "cost_per_booked_sr_inr": safe(bot_total, booked)},
            {"arm": "human_control", "contacts": contacts,
             "agreements": round(contacts * cm.AGREE_RATE_HUMAN),
             "booked_srs": round(contacts * cm.AGREE_RATE_HUMAN * cm.CONSENT_TO_BOOKING),
             "cost_per_contact_inr": round(per_min * human_pitch_min, 2),
             "cost_per_agreement_inr": round(
                 cm.cost_per_agreement(per_min * human_pitch_min, cm.AGREE_RATE_HUMAN), 2),
             "cost_per_booked_sr_inr": round(
                 cm.cost_per_booking(per_min * human_pitch_min, cm.AGREE_RATE_HUMAN), 2)},
        ],
        "assumptions": {
            "seat_cost_inr_month": seat, "talk_utilisation": cm.TALK_UTILISATION,
            "bot_cost_per_conversation_inr": round(bot_cost, 2),
            "human_agree_rate": cm.AGREE_RATE_HUMAN,
            "consent_to_booking": cm.CONSENT_TO_BOOKING,
            "source": "cost_model.py. None verified with the client.",
        },
        "caveat": ("The human arm is MODELLED from cost_model.py assumptions, not measured. "
                   "A real control arm requires a comparable human cohort over the same period "
                   "on the same segments."),
    }


# ---------------------------------------------------------------- content
@app.post("/content/scripts", tags=["content"], dependencies=[Depends(auth)])
def publish_script(body: dict):
    """Publishing is deliberately NOT implemented as a write.

    Content is a versioned directory validated by tools/validate_content.py, not an API upload.
    A BLC-approved script arriving over HTTP with no validation pass is precisely how an
    unreachable node or a missing disclosure reaches production - the validator exists so that
    cannot happen, and an endpoint that bypasses it would undo the whole control.
    """
    raise HTTPException(501, {
        "detail": "content is published as a validated pack, not uploaded",
        "how": ["tools/import_script.py --in <csv dir> --out packs/<name>",
                "tools/validate_content.py --pack packs/<name>   # must be 0 errors",
                "deploy with OUTBOUND_CONTENT_PACK=packs/<name>"],
        "current_pack": CONTENT.describe(),
    })


@app.post("/content/glossary", tags=["content"], dependencies=[Depends(auth)])
def publish_glossary(body: dict):
    return publish_script(body)


@app.get("/content/current", tags=["content"])
def current_content():
    """What is loaded right now. The content_hash here must match the one on every call record
    produced by this process - that is how a transcript is tied to the exact approved wording."""
    return CONTENT.describe()


if __name__ == "__main__":
    port = int(os.environ.get("OUTBOUND_API_PORT", "8078"))
    if not TOKEN:
        print("!! OUTBOUND_API_TOKEN is not set - the API is running UNAUTHENTICATED (dev only)")
    print(f"API on http://localhost:{port}   ·   docs at /docs")
    print(f"pack {CONTENT.pack_name} @ {CONTENT.content_hash} ({CONTENT.provenance})")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
