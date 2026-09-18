#!/usr/bin/env python3
"""Call console. Serves a browser page that talks to the engine over a WebSocket.

    python apps/server.py        then open http://localhost:8077

WHAT THIS IS AND IS NOT
-----------------------
Speech in and out is done by the BROWSER (Web Speech API), not by us. That makes a real,
interruptible, spoken conversation possible today with nothing to install - which is worth a
great deal for building and demonstrating the dialogue layer.

It is a HARNESS, not a component:

  - Chrome's recogniser is 16 kHz+ wideband cloud ASR. Our problem is 8 kHz telephony, where
    the same model's word error rate roughly doubles or triples (ADR-006).
  - It runs on Google's servers. That fails constraint 4 (India-resident inference) and makes it
    unusable in any runtime path that carries customer speech.
  - Its Indic coverage is not our language set, and it has no code-mixing guarantees.

So: use it to exercise dialogue, disclosure ordering, barge-in and our own latency. Do not use
it to form any view about Indic accuracy. That needs the corpus and our own benchmark harness.
Swapping it for a real ASR is one file - the browser fills the same role a streaming ASR will.
"""

import asyncio
import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import uvicorn                                                    # noqa: E402
from fastapi import FastAPI, WebSocket, WebSocketDisconnect       # noqa: E402
from fastapi.responses import FileResponse, Response              # noqa: E402

from engine import Content, Session                               # noqa: E402
from engine.machine import ComplianceError                        # noqa: E402
from engine.streaming import Endpointer, to_telephony              # noqa: E402
from engine.prerender import (INDEX_NAME, KokoroRenderer, WAV_CACHE,  # noqa: E402
                              cache_key, index_entry, split_spans)
from engine.ivr import Ivr                                        # noqa: E402


def _hold_music(seconds=4.0, sr=24000):
    """A short loopable hold tone, generated rather than shipped.

    Not decoration. A silent gap while the call is "connecting to an advisor" reads as a dropped
    call, and a demo that goes quiet at the handoff looks broken to the person watching. Real
    hold audio would be whatever SBI Card already licenses - this is a placeholder with no
    licensing question attached.
    """
    import numpy as np
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    # two alternating soft thirds, slow tremolo, fade at both ends so the loop does not click
    melody = np.zeros_like(t)
    for i, (a, b) in enumerate([(392.0, 493.9), (349.2, 440.0)]):
        seg = (t >= i * seconds / 2) & (t < (i + 1) * seconds / 2)
        melody[seg] = (np.sin(2 * np.pi * a * t[seg]) + 0.7 * np.sin(2 * np.pi * b * t[seg]))
    melody *= 0.11 * (0.75 + 0.25 * np.sin(2 * np.pi * 0.6 * t))
    edge = int(sr * 0.05)
    melody[:edge] *= np.linspace(0, 1, edge)
    melody[-edge:] *= np.linspace(1, 0, edge)
    return melody.astype("float32"), sr

# Real neural TTS, on this machine. ADR-005 says render each approved line once and play the
# file; this is that cache, filled lazily on first use rather than by a build step, so the
# console is usable without a separate pre-render pass.
# WAV_CACHE comes from engine.prerender so the console reads exactly where the renderer wrote -
# including when a render on a borrowed GPU pointed $VOICEAGENT_AUDIO_CACHE somewhere else.
WAV_CACHE.mkdir(parents=True, exist_ok=True)
try:
    TTS = KokoroRenderer()
    TTS_ERROR = None
except Exception as exc:                                           # noqa: BLE001
    TTS, TTS_ERROR = None, f"{type(exc).__name__}: {exc}"

HOLD_WAV = WAV_CACHE / "hold.wav"
if not HOLD_WAV.exists():
    import io as _io
    import soundfile as _sf
    _a, _sr = _hold_music()
    _buf = _io.BytesIO()
    _sf.write(_buf, _a, _sr, format="WAV", subtype="PCM_16")
    HOLD_WAV.write_bytes(_buf.getvalue())

# Our own ASR, loaded once at import. If the weights are absent the console still works on the
# browser recogniser - the point is that the real engine is optional scaffolding, not a hard
# dependency of the dialogue layer.
try:
    from engine.asr_engines import load_engine                     # noqa: E402
    ASR = load_engine("indic_conformer_ctc")
    ASR_ERROR = None
except Exception as exc:                                           # noqa: BLE001
    ASR, ASR_ERROR = None, f"{type(exc).__name__}: {exc}"

STATIC = pathlib.Path(__file__).resolve().parent / "static"
app = FastAPI(title="SBI Card outbound voice agent - call console")
CONTENT = Content()

# A slice of the calling base, so a demo call uses a real record rather than the example values
# in campaign_vars.yaml. Picking "Tushar, FlexiPay, 1.57 lakh eligible over three, six or nine
# months" is a different conversation from picking a placeholder.
BASE_CSV = pathlib.Path(__file__).resolve().parent.parent / "runs" / "base.csv"


def _load_base(per_bucket=8):
    """A balanced sample: a few records per (product, locale), so the picker is not 90% one
    product. Order is preserved, so the same base always yields the same demo list."""
    import csv
    from collections import Counter
    if not BASE_CSV.exists():
        return {}
    with open(BASE_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    counts, picked = Counter(), {}
    for row in rows:
        bucket = (row["product"], row["locale"])
        if counts[bucket] >= per_bucket:
            continue
        counts[bucket] += 1
        picked[row["masked_ref_id"]] = row
    return picked


BASE = _load_base()


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/config")
async def config():
    return {
        "products": sorted(CONTENT.products),
        "locales": CONTENT.locales,
        "content_versions": {p: v.version for p, v in CONTENT.products.items()},
        "pack": CONTENT.describe(),
        "tts": {
            "available": TTS is not None,
            "name": getattr(TTS, "name", None),
            "sample_rate": getattr(TTS, "sample_rate", None),
            "india_resident": getattr(TTS, "india_resident", None),
            "voices": {"en": ["af_heart", "af_bella", "bf_emma", "am_michael"],
                       "hi": ["hf_alpha", "hf_beta", "hm_omega", "hm_psi"]},
            "prerendered_engine": AUDIO_ENGINE,
            "prerendered_spans": len(AUDIO_INDEX),
            "error": TTS_ERROR,
        },
        "asr": {
            "available": ASR is not None,
            "name": getattr(ASR, "name", None),
            "languages": getattr(ASR, "languages", []),
            "validated": getattr(ASR, "validated", False),
            "india_resident": getattr(ASR, "india_resident", None),
            "error": ASR_ERROR,
        },
    }


@app.get("/api/customers")
async def customers():
    """The base, as the dialer would hand it to us - one record per call."""
    out = []
    for ref, row in BASE.items():
        label = f"{row['customer_first_name']} · {row['product']} · {row['locale']}"
        detail = ""
        if row["product"] == "flexipay" and row.get("eligible_amount"):
            detail = (f"Rs {int(row['eligible_amount']):,} over {row['tenure_options']}"
                      f" @ {row['roi_annual_pct']}%")
        elif row["product"] == "clip" and row.get("current_limit"):
            detail = f"Rs {int(row['current_limit']):,} -> Rs {int(row['enhanced_limit']):,}"
        elif row["product"] == "multicarding" and row.get("offered_card_name"):
            detail = f"{row['offered_card_name']}, fee Rs {row['annual_fee']}"
        out.append({"ref": ref, "label": label, "detail": detail,
                    "name": row["customer_first_name"], "product": row["product"],
                    "locale": row["locale"], "zone": row.get("zone", "")})
    return {"customers": out, "source": str(BASE_CSV.name) if BASE else None}


def _campaign_for(ref):
    """Campaign variables for one base record. Falls back to the declared examples."""
    row = BASE.get(ref)
    if not row:
        return CONTENT.example_campaign()
    campaign = {k: v for k, v in row.items()
                if k not in ("masked_ref_id", "product", "locale", "zone") and v != ""}
    for key in ("tenure_months", "offer_valid_days", "min_txn_amt", "eligible_amount",
                "processing_fee", "indicative_emi", "current_limit", "enhanced_limit",
                "joining_fee", "annual_fee"):
        if key in campaign:
            campaign[key] = int(campaign[key])
    return campaign


def _state(session):
    m = session.machine
    return {
        "node": m.current,
        "kind": m.node.kind if m.current else None,
        "listening": m.listening,
        "finished": m.finished,
        "disposition": m.disposition,
        "disclosures": list(m.played_disclosures),
        "path": [u.id for u in m.history if u.kind == "node"],
    }


def _audio_key(text, locale, voice):
    return cache_key(text, locale, voice, TTS.name, TTS.version)


@app.get("/audio/{key}.wav")
async def audio(key: str):
    path = WAV_CACHE / f"{key}.wav"
    if not path.exists():
        return Response(status_code=404)
    return FileResponse(path, media_type="audio/wav")


def _load_audio_index():
    """Map (locale, voice, text) -> filename, written by tools/prerender_audio.py.

    ADR-005: the serving box plays files and never loads a TTS model. Resolving audio through
    this index rather than through a live renderer's cache key is what makes that true - the
    audio can be rendered on a GPU box, by a different engine, weeks earlier, and production
    needs nothing but the files and this JSON.
    """
    path = WAV_CACHE / INDEX_NAME
    if not path.exists():
        return {}, None
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc.get("spans", {}), doc.get("engine")


AUDIO_INDEX, AUDIO_ENGINE = _load_audio_index()


def _render_span(text, locale, voice="default"):
    hit = AUDIO_INDEX.get(index_entry(locale, voice, text))
    if hit and (WAV_CACHE / hit).exists():
        return f"/audio/{hit}"
    if TTS is None:
        return None
    # Miss: a per-customer value (a name, an amount) or content added since the last
    # pre-render. Synthesise now and cache under this engine's key.
    key = _audio_key(text, locale, voice)
    path = WAV_CACHE / f"{key}.wav"
    if not path.exists():
        path.write_bytes(TTS.render_wav(text, locale, voice))
    return f"/audio/{key}.wav"


def _render(raw, rendered, campaign, locale, voice="default"):
    """ADR-005 at playback time.

    Split the APPROVED TEMPLATE - slots intact - not the rendered line. That is the whole trick:
    "Am I speaking with {customer_first_name}?" is one fixed span every customer shares plus one
    short live span. Splitting the rendered line instead caches "Am I speaking with Sushane?"
    per customer and pays a full synthesis on every call, which is what ADR-005 exists to avoid.

    Fixed spans are cache hits from tools/prerender_audio.py. Only slot-bearing spans are
    synthesised now, and those are a name or an amount - a second of speech, not a sentence.
    """
    if TTS is None:
        return []
    if not (raw or "").strip():
        raw = rendered
    clips = []
    for span in split_spans(raw):
        text = span.text.strip()
        if not text:
            continue
        if span.fixed:
            clips.append(_render_span(text, locale, voice))
        else:
            slot = text.strip("{}")
            value = campaign.get(slot)
            if value not in (None, ""):
                clips.append(_render_span(str(value), locale, voice))
    return clips


async def _spoke(rec, session=None, locale="en", voice="default"):
    """Resolve audio for a turn WITHOUT blocking the event loop.

    A cache hit is a dict lookup and costs nothing. A miss is a live synthesis - seconds on CPU -
    and running that inline froze the whole server: the websocket keepalive timed out and the
    call dropped. In production it would have stalled every concurrent session, not just the one
    doing the synthesising.

    So the work moves to a thread. This is the difference between a demo that works when the
    cache happens to be warm and a server that works when it is not.
    """
    campaign = session.machine.campaign if session else {}
    out = []
    for kind, ident, txt, raw in rec.spoke:
        audio = await asyncio.to_thread(_render, raw, txt, campaign, locale, voice)
        out.append({"kind": kind, "id": ident, "text": txt, "audio": audio})
    return out


# Locale -> the ASR's language code. Our pack says "hi_latn" (romanised Hindi); the model
# knows "hi". English is NOT in this model - its 22 languages are the scheduled Indian ones -
# so en falls back to the browser recogniser and the UI says so.
# A session with no ceiling is a leak. A real call has two hard limits and a socket must have
# the same ones: nobody talks to an outbound bot for ten minutes, and a customer who has gone
# silent for ninety seconds has put the phone down. Without these, every abandoned browser tab
# holds a Session, a Machine and a router reference until the process restarts.
MAX_CALL_SECONDS = 600
IDLE_TIMEOUT_SECONDS = 90

ASR_LANG = {"hi_latn": "hi", "ta": "ta", "te": "te", "kn": "kn",
            "ml": "ml", "mr": "mr", "gu": "gu", "bn": "bn"}
LOCALE_OF = {v: k for k, v in ASR_LANG.items()}

# How much better a rival language must score before we change the call's language. Switching
# on a narrow margin is worse than not switching: the customer hears the bot lurch between
# languages mid-conversation. UNVALIDATED - needs real code-mixed audio to tune (ADR-006).
SWITCH_MARGIN = 0.35


async def _handle_utterance(sock, state, audio):
    """One endpointed utterance: our ASR, then the dialogue engine."""
    import time
    session = state["session"]
    lang = ASR_LANG.get(state["locale"])
    if ASR is None or lang is None:
        return

    if state["telephony"]:
        audio = to_telephony(audio)

    # Every language the loaded pack actually has content for. Offering a language we cannot
    # speak back in would be worse than not detecting it.
    candidates = [ASR_LANG[loc] for loc in CONTENT.locales if loc in ASR_LANG]
    if lang not in candidates:
        candidates.append(lang)

    t0 = time.perf_counter()
    try:
        best, heard, score, ranked = await asyncio.to_thread(ASR.detect, audio, candidates)
    except Exception as exc:                                       # noqa: BLE001
        await sock.send_text(json.dumps({"type": "error", "detail": f"asr: {exc}"}))
        return
    asr_ms = round((time.perf_counter() - t0) * 1000, 1)

    # Language switching, and why it is free: the 600M encoder ran once above and every
    # candidate language was decoded from the same output for ~0.5 ms each. Switching the call
    # then costs nothing downstream either - ADR-005 pre-renders every approved line in every
    # locale, so the new language is a different cache key, not a synthesis.
    switched = None
    current = next((r for r in ranked if r[0] == lang), None)
    if best and best != lang and current and (score - current[2]) > SWITCH_MARGIN:
        new_locale = LOCALE_OF.get(best)
        if new_locale in CONTENT.locales and session.machine.switch_locale(new_locale):
            state["locale"] = new_locale
            switched = {"from": lang, "to": best, "margin": round(score - current[2], 3)}
        else:
            heard = current[1]        # no content in that language: keep the call as it was
            best = lang
    else:
        heard = current[1] if current else heard

    await sock.send_text(json.dumps({
        "type": "asr", "text": heard, "asr_ms": asr_ms,
        "audio_ms": round(len(audio) / 16000 * 1000),
        "rtf": round(asr_ms / max(len(audio) / 16, 1e-6), 3),
        "telephony": state["telephony"], "engine": ASR.name,
        "language": best, "switched": switched,
        "candidates": [{"lang": l, "score": round(s, 2)} for l, _, s in ranked[:4]]}))

    if switched:
        token = CONTENT.backchannel("language_switched", state["locale"])
        if token:
            await sock.send_text(json.dumps({
                "type": "say", "utterances": [
                    {"kind": "backchannel", "id": "BC_LANGUAGE_SWITCHED", "text": token,
                     "audio": await asyncio.to_thread(
                         _render, token, token, {}, state["locale"])}],
                "state": _state(session)}))

    if heard.strip():
        await _say(sock, session, heard)


async def _say_payload(rec, session, locale, voice="default"):
    """The single place a `say` message is constructed.

    There were two of these, built by hand, and they drifted: `mood` reached the client on the
    speech path and not on the typed path. At production bar, a wire contract with two authors
    is a defect waiting for a field to be added.
    """
    return {
        "type": "say",
        "utterances": await _spoke(rec, session, locale, voice),
        "heard": rec.utterance,
        "route": {"kind": rec.route_kind, "id": rec.route_id,
                  "confidence": rec.confidence, "band": rec.band,
                  "alternatives": rec.alternatives},
        "timing": {"router_ms": rec.router_ms, "policy_ms": rec.policy_ms,
                   "engine_ms": rec.engine_ms},
        "mood": {"label": rec.sentiment, "polarity": rec.polarity},
        "state": _state(session),
    }


async def _say(sock, session, text):
    try:
        rec = session.say(text)
    except ComplianceError as exc:
        await sock.send_text(json.dumps({"type": "compliance_stop", "detail": str(exc)}))
        return
    except RuntimeError as exc:
        await sock.send_text(json.dumps({"type": "error", "detail": str(exc)}))
        return
    await sock.send_text(json.dumps(
        await _say_payload(rec, session, session.locale)))
    if session.finished:
        await _after_transfer(sock, state, session)


async def _ivr_say(sock, ivr, key, extra=None):
    text = ivr.line(key)
    await sock.send_text(json.dumps({
        "type": "ivr", "prompt_key": key, "text": text,
        "audio": (await asyncio.to_thread(_render, text, text, {}, ivr.locale)) if text else [],
        "dialpad": not ivr.finished and ivr.has_ivr,
        "operator": ivr.operator, "mechanism": ivr.type,
        **(extra or {})}))


def _evidence(payload, session):
    """The four compliance rules, computed on the live call. Same logic as
    GET /calls/{id}/evidence - the console must not show a friendlier answer than the audit."""
    approved = set(CONTENT.faq) | set(CONTENT.disclosures)
    for prod in CONTENT.products.values():
        approved |= set(prod.nodes)
    spoken = [(u.kind, u.id) for u in session.machine.history]
    unapproved = [i for k, i in spoken if not i.startswith("BC_") and i not in approved]
    discl = payload.get("disclosures_played") or []
    pitched = any(i.startswith("N04") for _, i in spoken)
    return [
        {"rule": "identity_before_disclosure",
         "pass": (discl[:1] == ["D01_IDENTITY"]) if discl else True},
        {"rule": "disclosure_before_pitch",
         "pass": (not pitched) or {"D01_IDENTITY", "D02_RECORDED_LINE"} <= set(discl)},
        {"rule": "no_unapproved_utterance", "pass": not unapproved, "detail": unapproved[:4]},
        {"rule": "agreement_requires_terms",
         "pass": payload.get("disposition") != "AGREED_TRANSFERRED"
                 or any(d.endswith("_TERMS") for d in discl)},
    ]


async def _finish(sock, session, ivr=None):
    payload = session.handoff_payload()
    await sock.send_text(json.dumps({
        "type": "end", "disposition": session.machine.disposition,
        "payload": payload,
        # handoff.yaml `inbound`: what comes back to us from the advisor side.
        "inbound": ivr.to_inbound() if ivr else None,
        "evidence": _evidence(payload, session),
        "latency": session.latency_summary()}))


async def _after_transfer(sock, state, session):
    """Everything past our boundary. Simulated and labelled - see engine/ivr.py."""
    if session.machine.disposition != "AGREED_TRANSFERRED":
        await _finish(sock, session)
        return

    ivr = Ivr(CONTENT, session.product, state["locale"])
    state["ivr"] = ivr
    hold = ivr.line("hold")
    await sock.send_text(json.dumps({
        "type": "transfer", "operator": ivr.operator, "mechanism": ivr.type,
        "hold_ms": ivr.hold_ms, "hold_audio": "/audio/hold.wav",
        "text": hold,
        "audio": (await asyncio.to_thread(_render, hold, hold, {}, ivr.locale)) if hold else [],
        "note": "advisor-side, simulated (OI-1 unresolved)"}))

    result = ivr.start()
    if result.state == "no_ivr":
        await _ivr_say(sock, ivr, "offer")
        await _finish(sock, session, ivr)
        return
    await _ivr_say(sock, ivr, "offer")


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    session = None
    state = {"session": None, "locale": "en", "telephony": False, "voice": "default",
             "ivr": None, "opened": time.monotonic(), "last_activity": time.monotonic(),
             "endpointer": Endpointer(), "tail": np.zeros(0, dtype=np.float32)}
    try:
        while True:
            try:
                packet = await asyncio.wait_for(sock.receive(),
                                                timeout=IDLE_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                await sock.send_text(json.dumps({
                    "type": "timeout", "reason": "idle",
                    "detail": f"no activity for {IDLE_TIMEOUT_SECONDS}s - closing the leg"}))
                break

            now = time.monotonic()
            if state["session"] and now - state["opened"] > MAX_CALL_SECONDS:
                await sock.send_text(json.dumps({
                    "type": "timeout", "reason": "max_duration",
                    "detail": f"call exceeded {MAX_CALL_SECONDS}s - closing the leg"}))
                break
            state["last_activity"] = now

            # Binary frames are raw PCM16 mono @16 kHz from the browser's AudioWorklet.
            if "bytes" in packet and packet["bytes"] is not None:
                if state["session"] is None or ASR is None:
                    continue
                pcm = np.frombuffer(packet["bytes"], dtype=np.int16).astype(np.float32) / 32768.0
                chunk = np.concatenate([state["tail"], pcm])
                frames = len(chunk) // 320
                state["tail"] = chunk[frames * 320:]
                for i in range(frames):
                    utterance, started = state["endpointer"].push(chunk[i * 320:(i + 1) * 320])
                    if started:
                        await sock.send_text(json.dumps({"type": "speech_start"}))
                    if utterance is not None:
                        await _handle_utterance(sock, state, utterance)
                continue

            if "text" not in packet or packet["text"] is None:
                continue
            msg = json.loads(packet["text"])
            kind = msg.get("type")

            if kind == "dtmf" and state.get("ivr"):
                ivr = state["ivr"]
                result = ivr.press(msg.get("key", ""))
                await _ivr_say(sock, ivr, result.prompt_key,
                               {"state": result.state, "attempts": result.attempts})
                if result.finished:
                    await _finish(sock, state["session"], ivr)
                continue

            if kind == "set_mode":
                state["telephony"] = bool(msg.get("telephony"))
                if msg.get("voice"):
                    state["voice"] = msg["voice"]
                continue

            if kind == "start":
                state["ivr"] = None
                state["endpointer"] = Endpointer()
                state["tail"] = np.zeros(0, dtype=np.float32)
                state["locale"] = msg.get("locale", "en")
                ref = msg.get("masked_ref_id")
                row = BASE.get(ref)
                product = (row or {}).get("product") or msg.get("product", "flexipay")
                locale = (row or {}).get("locale") or msg.get("locale", "en")
                state["locale"] = locale
                session = Session(
                    CONTENT, product, _campaign_for(ref), locale=locale,
                    masked_ref_id=ref or "SBIC-DEMO-0001")
                state["session"] = session
                rec = session.start()
                await sock.send_text(json.dumps({
                    "type": "say", "utterances": await _spoke(rec, session, state["locale"], state["voice"]),
                    "state": _state(session),
                    "correlation_id": session.correlation_id}))

            elif kind == "said" and session:
                text = (msg.get("text") or "").strip()
                if not text:
                    continue
                try:
                    rec = session.say(text)
                except ComplianceError as exc:
                    await sock.send_text(json.dumps({"type": "compliance_stop",
                                                     "detail": str(exc)}))
                    continue
                except RuntimeError as exc:
                    await sock.send_text(json.dumps({"type": "error", "detail": str(exc)}))
                    continue

                await sock.send_text(json.dumps(
                    await _say_payload(rec, session, state["locale"], state["voice"])))

                if session.finished:
                    await _after_transfer(sock, state, session)

            elif kind == "barge" and session:
                # DESIGN 2.3 step 4. A line the customer talked over was not heard in full, so
                # logging it as played would put a false record in the audit trail.
                session.note_truncation(msg.get("node_id", "?"), int(msg.get("played_ms", 0)))

    except WebSocketDisconnect:
        pass
    except Exception as exc:                                       # noqa: BLE001
        await sock.send_text(json.dumps({"type": "error", "detail": repr(exc)}))


if __name__ == "__main__":
    print("call console on http://localhost:8077   (Chrome or Edge - needs Web Speech API)")
    uvicorn.run(app, host="127.0.0.1", port=8077, log_level="warning")
