"""The dialogue policy. Deterministic, inspectable, and the only thing that decides what is said.

RESEARCH 2.1: every serious framework converges on the same split - LLM for dialogue
UNDERSTANDING, deterministic engine for dialogue POLICY. The router understands. This decides.

RESEARCH 2.2 is why: frontier function-calling agents score below 25% on tau-bench pass^8, and
policy adherence degrades measurably as a conversation lengthens. So the phase is tracked here,
explicitly, rather than trusted to a model that is holding it in a prompt.

The disclosure check below duplicates C5 in tools/validate_content.py on purpose. The validator
proves the graph cannot express a violation; this refuses to execute one. Static proof and
runtime guard fail differently, and the thing they are guarding is an undisclosed offer on a
recorded line at a bank.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


# Repeating the same line a third time is not helping anyone; hand over instead.
MAX_REPLAYS = 2


class ComplianceError(RuntimeError):
    """A node was about to play without a disclosure it requires. Never caught, never softened."""


@dataclass
class Utterance:
    kind: str            # "node" | "disclosure" | "faq" | "backchannel"
    id: str
    text: str            # campaign variables substituted - what the customer hears
    raw: str = ""        # the approved template, slots intact
    locale: str = ""     # the language it was actually spoken in
    """`raw` exists so the audio layer can split the line the way the pack declared it.

    Without it the renderer only sees "Am I speaking with Sushane?" and caches that per
    customer, which defeats ADR-005 completely - every call pays a full synthesis. With it,
    "Am I speaking with {customer_first_name}?" is one cached fixed span plus one short live
    one, and the cached half is shared by every customer.
    """


@dataclass
class Turn:
    utterances: list = field(default_factory=list)
    route: object = None
    node_before: str | None = None
    node_after: str | None = None


class Machine:
    LISTENING = "normal"
    ENDING = ("terminal", "transfer")

    def __init__(self, content, product: str, campaign: dict, locale: str = "en"):
        self.content = content
        self.product = content.products[product]
        self.campaign = campaign
        self.locale = locale

        self.current: str | None = None
        self.played_disclosures: list[str] = []
        self.visits: Counter = Counter()
        self.resume_target: str | None = None
        self.history: list[Utterance] = []
        self.turns: list[Turn] = []
        self.abandoned = False
        self.replays: Counter = Counter()
        self.visit_variant: Counter = Counter()   # rotates approved phrasings per node
        self.moods: list = []
        self.locale_history: list = [locale]

    def switch_locale(self, locale: str) -> bool:
        """Change the language mid-call. Costs nothing.

        Node ids do not change - only the key used to look up the approved line and its
        pre-rendered audio. Because ADR-005 renders every line in every locale offline, a
        language switch is a different cache lookup, not a synthesis. The state machine, the
        disclosures already played and the audit trail all carry straight over.

        Disclosures stay satisfied across a switch: the customer heard them, in whatever
        language they were played. The audit records which, per utterance, so a reviewer can
        answer "was the rate disclosed, and in what language" - which is the question that
        actually gets asked.
        """
        if locale == self.locale:
            return False
        self.locale = locale
        self.locale_history.append(locale)
        return True

    def hang_up(self):
        """The customer stopped responding or dropped the line. Not a disposition the script
        produces, but one that really happens, and it must appear in the funnel rather than
        leave a call with no outcome at all."""
        self.abandoned = True

    # -- state ---------------------------------------------------------------

    @property
    def node(self):
        return self.product.nodes[self.current]

    @property
    def finished(self) -> bool:
        return self.current is not None and self.node.kind in self.ENDING

    @property
    def disposition(self):
        if self.finished:
            return self.node.disposition
        return "CUSTOMER_HUNG_UP" if self.abandoned else None

    @property
    def listening(self) -> bool:
        return self.current is not None and self.node.kind == self.LISTENING

    # -- playing -------------------------------------------------------------

    def _play(self, node_id: str) -> list[Utterance]:
        node = self.product.nodes[node_id]

        missing = [d for d in node.requires_disclosure if d not in self.played_disclosures]
        if missing:
            raise ComplianceError(
                f"{self.product.name}:{node_id} requires {', '.join(missing)} "
                f"but only {self.played_disclosures or ['nothing']} has played")

        out = []
        # Rotate through the approved phrasings so a re-prompt is not word-for-word identical.
        variant = self.visit_variant[node_id]
        self.visit_variant[node_id] += 1
        raw = self.content.node_template(self.product.name, node_id, self.locale, variant)
        text = self.content.render(raw, self.campaign) if raw else ""
        if text:
            out.append(Utterance("node", node_id, text, raw, self.locale))
        for did in node.plays_disclosure:
            draw = " ".join(self.content.disclosures[did]["line"][self.locale].split())
            out.append(Utterance("disclosure", did,
                                 self.content.disclosure_line(did, self.locale, self.campaign),
                                 draw, self.locale))
            self.played_disclosures.append(did)

        self.visits[node_id] += 1
        self.history.extend(out)
        return out

    def _advance_to(self, node_id: str) -> list[Utterance]:
        """Play node_id, then keep playing through `chain` nodes until we listen or we end."""
        out = []
        seen = set()
        while True:
            if node_id in seen:                      # a chain that loops is a hang, not a call
                raise RuntimeError(f"chain loop at {node_id}")
            seen.add(node_id)
            self.current = node_id
            out += self._play(node_id)
            node = self.product.nodes[node_id]
            if node.kind != "chain":
                return out
            node_id = node.next

    # -- driving -------------------------------------------------------------

    def start(self) -> Turn:
        turn = Turn(node_before=None)
        turn.utterances = self._advance_to(self.product.entry)
        turn.node_after = self.current
        self.turns.append(turn)
        return turn

    def handle(self, route) -> Turn:
        """Apply one routing decision. The router chose the id; this decides what happens."""
        if self.finished:
            raise RuntimeError(
                f"call already ended at {self.current} ({self.disposition}); "
                "the leg belongs to the dialer now")
        turn = Turn(route=route, node_before=self.current)
        node = self.node

        if route.kind == "faq" and node.faq_enabled:
            text = self.content.faq_answer(route.id, self.locale, self.campaign)
            utt = Utterance("faq", route.id, text,
                            self.content.faq[route.id].answer.get(self.locale, ""), self.locale)
            said = self.mood_backchannel() or self.say_backchannel("before_answer")
            self.history.append(utt)
            turn.utterances = ([said] if said else []) + [utt]
            turn.node_after = self.current
            self.turns.append(turn)
            return turn

        target = self._target_for(route)

        if target == "__REPLAY__":
            self.replays[self.current] += 1
            if self.replays[self.current] > MAX_REPLAYS:
                turn.utterances = self._advance_to(
                    self.product.global_routes["OUT_OF_SCOPE"])
            else:
                turn.utterances = self._play(self.current)
        elif target == "__RESUME__":
            turn.utterances = self._advance_to(self.resume_target or self.current)
        else:
            # Entering a global handler from a listening node: remember where to come back to.
            if target in self.product.global_routes.values() and node.kind == self.LISTENING:
                self.resume_target = self.current
            said = self.mood_backchannel()
            turn.utterances = (([said] if said else [])
                               + self._advance_to(self._apply_visit_cap(target)))

        turn.node_after = self.current
        self.turns.append(turn)
        return turn

    def note_mood(self, label: str):
        """Record the customer's mood for this turn and let it choose the acknowledgement.

        A human agent does not open with the pitch after being snapped at - they soften first.
        This is the same move, inside the closed set: the mood only selects WHICH approved
        token plays, never what is said about the product.
        """
        self.moods.append(label)

    def mood_backchannel(self):
        """The acknowledgement the current mood calls for, if any."""
        mood = self.moods[-1] if self.moods else None
        category = {"irritated": "soften", "negative": "soften",
                    "confused": "before_answer", "positive": "acknowledge"}.get(mood)
        return self.say_backchannel(category) if category else None

    def say_backchannel(self, category: str):
        """An approved acknowledgement token, or nothing. Never generated, never a claim."""
        token = self.content.backchannel(category, self.locale)
        if not token:
            return None
        utt = Utterance("backchannel", f"BC_{category.upper()}", token, token, self.locale)
        self.history.append(utt)
        return utt

    def _target_for(self, route) -> str:
        node = self.node
        if route.kind == "intent":
            if route.id in node.routes:
                return node.routes[route.id]
            if route.id in self.product.global_routes:
                return self.product.global_routes[route.id]
        if route.kind == "out_of_scope":
            for cat in self.content.out_of_scope["categories"]:
                if cat["id"] == route.id and cat.get("route"):
                    return cat["route"]
            return self.product.global_routes["OUT_OF_SCOPE"]
        # An in-scope id with nowhere to go at this node is, by definition, out of scope here.
        return self.product.global_routes["OUT_OF_SCOPE"]

    def _apply_visit_cap(self, node_id: str) -> str:
        node = self.product.nodes[node_id]
        if node.max_visits and self.visits[node_id] >= node.max_visits:
            return node.on_max_visits or node_id
        return node_id
