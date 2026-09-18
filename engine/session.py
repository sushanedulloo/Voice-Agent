"""One call. Wires router to machine, and produces the audit artefact as it goes.

CLAUDE.md: instrumentation is a first-class feature, not something added at the end. The
engagement is judged on a defensible cost-per-booked-SR number with a human control arm beside
it, and none of that exists unless every turn is recorded as it happens.

So the handoff payload is not a reporting job that runs later over a database. It is assembled
during the call, field for field against content/handoff.yaml, and it is what crosses our
boundary at transfer.
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field

from .machine import Machine
from .sentiment import score_call, score_turn
from .router import Router

# The router is expensive to build (it fits a vectoriser over the whole example corpus) and is
# immutable once built. Building one per call would refit it 20.4 lakh times a month to get the
# identical object back. Keyed by locale because the index is locale-independent but the class
# takes one; content is process-global and reloaded by restarting.
_ROUTERS: dict = {}


def router_for(content, locale: str) -> Router:
    key = (id(content), locale)
    if key not in _ROUTERS:
        _ROUTERS[key] = Router(content, locale=locale)
    return _ROUTERS[key]

# Constraint 3. Cheap, deterministic, and runs on the payload rather than trusting that no code
# path ever put a PAN in it. RESEARCH 2.5: inline controls are O(1) checks, never model calls.
PAN_LIKE = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
LONG_DIGITS = re.compile(r"\b\d{6,}\b")


class PIILeak(RuntimeError):
    """Something PII-shaped reached a field that crosses our boundary."""


@dataclass
class TurnRecord:
    index: int
    utterance: str | None
    route_kind: str | None
    route_id: str | None
    confidence: float | None
    band: str | None
    node_before: str | None
    node_after: str | None
    spoke: list = field(default_factory=list)
    router_ms: float = 0.0
    policy_ms: float = 0.0
    sentiment: str | None = None
    polarity: float | None = None
    alternatives: list = field(default_factory=list)

    @property
    def engine_ms(self) -> float:
        return round(self.router_ms + self.policy_ms, 2)


class Session:
    def __init__(self, content, product: str, campaign: dict, locale: str = "en",
                 masked_ref_id: str = "SBIC-TEST-0000", campaign_id: str = "TEST"):
        self.content = content
        self.product = product
        self.locale = locale
        self.masked_ref_id = masked_ref_id
        self.campaign_id = campaign_id
        self.correlation_id = str(uuid.uuid4())

        self.router = router_for(content, locale)
        self.machine = Machine(content, product, campaign, locale=locale)

        self.records: list[TurnRecord] = []
        self.truncated: list[dict] = []
        self.started_at = time.time()

    # -- driving -------------------------------------------------------------

    def start(self) -> TurnRecord:
        t0 = time.perf_counter()
        turn = self.machine.start()
        rec = TurnRecord(
            index=0, utterance=None, route_kind=None, route_id=None, confidence=None,
            band=None, node_before=None, node_after=turn.node_after,
            spoke=[(u.kind, u.id, u.text, u.raw) for u in turn.utterances],
            policy_ms=round((time.perf_counter() - t0) * 1000, 2))
        self.records.append(rec)
        return rec

    def say(self, utterance: str) -> TurnRecord:
        """The customer said something. Route it, apply the policy, return what we say back."""
        t0 = time.perf_counter()
        route = self.router.route(utterance, self.product, self.machine.node)
        t1 = time.perf_counter()
        # FR-701. Lexicon, ~microseconds - it fits inside the turn budget where a classifier
        # would not (RESEARCH 2.5 leaves 50-100 ms for ALL inline work).
        mood = score_turn(utterance)
        self.machine.note_mood(mood.label)
        turn = self.machine.handle(route)
        t2 = time.perf_counter()

        rec = TurnRecord(
            index=len(self.records), utterance=utterance,
            route_kind=route.kind, route_id=route.id, confidence=route.confidence,
            band=route.band, node_before=turn.node_before, node_after=turn.node_after,
            spoke=[(u.kind, u.id, u.text, u.raw) for u in turn.utterances],
            router_ms=round((t1 - t0) * 1000, 2), policy_ms=round((t2 - t1) * 1000, 2),
            alternatives=route.alternatives,
            sentiment=mood.label, polarity=mood.polarity)
        self.records.append(rec)
        return rec

    def note_truncation(self, node_id: str, played_ms: int):
        """Barge-in cut playback. DESIGN 2.3 step 4 - a line the customer did not hear in full
        was not disclosed in full, so logging it as played would be a false audit record."""
        self.truncated.append({"utterance_id": node_id, "played_ms": played_ms})

    # -- the artefact --------------------------------------------------------

    @property
    def finished(self) -> bool:
        return self.machine.finished

    def handoff_payload(self) -> dict:
        """Exactly the `outbound` block of content/handoff.yaml.

        Note what is not here and cannot be: any campaign variable marked `pii: true` in
        campaign_vars.yaml. The customer's first name is spoken on the call and then dropped -
        it is never logged, never returned, never correlated. Constraint 3 is not "we try not
        to store PII", it is "there is no field for it".
        """
        m = self.machine
        agreement = next((r.confidence for r in reversed(self.records)
                          if r.route_kind == "intent" and r.route_id == "AGREE"), None)
        payload = {
            "masked_ref_id": self.masked_ref_id,
            "correlation_id": self.correlation_id,
            "campaign_id": self.campaign_id,
            "product": self.product,
            "language_used": self.locale,
            "bot_duration_ms": int((time.time() - self.started_at) * 1000),
            "turn_count": len([r for r in self.records if r.utterance is not None]),
            "nodes_played": [u.id for u in m.history if u.kind == "node"],
            "disclosures_played": list(m.played_disclosures),
            "faqs_answered": [{"id": r.route_id, "band": r.band}
                              for r in self.records if r.route_kind == "faq"],
            "truncated_utterances": self.truncated,
            "content_version": m.product.version,
            # The hash, not just the version. A version string is a claim someone remembered to
            # bump; the hash is evidence, and it is what ties this transcript to the exact bytes
            # of approved wording that spoke. The evidence packet is worthless without it.
            "content_hash": self.content.content_hash,
            "content_provenance": self.content.provenance,
            "disposition": m.disposition,
            "agreement_confidence": agreement,
            "escalation_flags": self._flags(),
            # What the advisor most wants in the first second of a warm transfer: the mood they
            # are walking into. A disposition code cannot carry "agreed, but irritated".
            "sentiment": self.sentiment().to_dict(),
            "recording_pointer": None,       # the partner's recorder owns this; we point, not copy
        }
        _assert_no_pii(payload)
        for slot, spec in self.content.vars["slots"].items():
            if spec.get("pii") and slot in payload:
                raise PIILeak(f"pii-marked campaign variable {slot!r} reached the payload")
        return payload

    def sentiment(self):
        """FR-701 aggregate for this call."""
        return score_call([r.utterance for r in self.records if r.utterance])

    def _flags(self) -> list:
        flags = []
        if self.machine.finished and self.machine.node.escalate:
            flags.append(self.machine.node.disposition)
        if self.sentiment().escalating:
            flags.append("SENTIMENT_ESCALATING")
        for r in self.records:
            if r.route_kind == "out_of_scope":
                for cat in self.content.out_of_scope["categories"]:
                    if cat["id"] == r.route_id and cat.get("priority") == "urgent":
                        flags.append(cat["id"])
        return sorted(set(flags))

    def latency_summary(self) -> dict:
        spoken = [r.engine_ms for r in self.records if r.utterance is not None]
        if not spoken:
            return {}
        spoken.sort()
        return {
            "turns": len(spoken),
            "p50_engine_ms": spoken[len(spoken) // 2],
            "max_engine_ms": spoken[-1],
        }


# Fields we generate ourselves, whose shape we assert instead of scanning. A UUID's first
# segment is eight hex characters and is all-digits roughly 2% of the time, so a blanket
# "six or more digits" scan flags our own correlation id at random. A guard that false-positives
# is worse than no guard: it gets switched off by whoever is on call at 3am, and then the real
# check is gone too.
STRUCTURAL = {
    "correlation_id": re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                                 r"[0-9a-f]{4}-[0-9a-f]{12}$"),
    "masked_ref_id": re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{2,63}$"),
}


def _assert_no_pii(payload: dict):
    def walk(value, path, field):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, f"{path}.{k}", k)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, f"{path}[{i}]", field)
        elif isinstance(value, str):
            # Shape first, and only for fields we generate ourselves. An exact-format check is
            # strictly stronger than the heuristics below, so running those afterwards can only
            # produce false alarms: a UUID whose first three segments happen to be all digits
            # ("12345678-9012-3456-...") matches PAN_LIKE exactly. Roughly one UUID in 1,150.
            if field in STRUCTURAL:
                if not STRUCTURAL[field].match(value):
                    raise PIILeak(f"{path} is not the identifier shape it claims to be")
                return
            if PAN_LIKE.search(value):
                raise PIILeak(f"{path} carries a card-number-shaped value")
            if LONG_DIGITS.search(value):
                raise PIILeak(f"{path} carries a PII-shaped value")
    walk(payload, "payload", "payload")
