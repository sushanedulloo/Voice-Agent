"""The post-transfer acceptance journey. Simulated, because it is not ours.

    READ THIS BEFORE BUILDING ON IT
    -------------------------------
    All three flowcharts put this AFTER our transfer and in the ADVISOR's hands:
    "Post-consent, the advisor guides the customer through a secured IVR, where the customer
    confirms acceptance of the offer by pressing option 1" (CH-FLEXIPAY 11a, CH-CLIP 11b).

    The charter's process map disagrees - it reads "BOT to take customer through IVR (for CLIP)".
    That contradiction is open item OI-1 and it is not ours to close. Until it is closed this
    module is a SIMULATION of somebody else's system, present so a demo can show the whole
    journey end to end rather than stopping at a handoff.

    If OI-1 resolves toward the bot, this stops being a simulation and becomes a regulated
    consent-capture component: DTMF capture, consent artefact storage, retention, and a
    materially larger InfoSec surface. It would then need to be rebuilt rather than promoted.

    Everything except four facts is invented and marked `invented:` in acceptance.yaml. The four
    facts: press 1 to accept; outcomes are accepted or rejected; accepted raises an SR
    automatically in SBIC; multicarding has no IVR and uses a C2B link plus an OTP instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IvrResult:
    state: str                    # prompt | invalid | accepted | rejected | exhausted | no_ivr
    prompt_key: str | None        # which line in acceptance.yaml to speak
    finished: bool = False
    accepted: bool | None = None
    attempts: int = 0
    keys: list = field(default_factory=list)


class Ivr:
    """One acceptance journey. Driven entirely by content/acceptance.yaml."""

    def __init__(self, content, product: str, locale: str = "en"):
        self.content = content
        self.product = product
        self.locale = locale
        spec = content.acceptance["mechanisms"][product]
        self.type = spec["type"]
        self.operator = spec["operator"]
        self.given = spec.get("given", {})
        self.invented = spec.get("invented", {})

        # prompts_from lets CLIP borrow FlexiPay's wording rather than duplicating it
        source = self.invented.get("prompts_from")
        if source:
            self.prompts = (content.acceptance["mechanisms"][source]["invented"]["prompts"])
        else:
            self.prompts = self.invented.get("prompts", {})

        self.accept_key = str(self.given.get("accept_key", "1"))
        self.max_attempts = int(self.invented.get("max_attempts", 2))
        self.hold_ms = int(self.invented.get("hold_ms", 2500))
        self.attempts = 0
        self.keys: list = []
        self.finished = False
        self.accepted: bool | None = None

    @property
    def has_ivr(self) -> bool:
        return self.type == "ivr_dtmf"

    def line(self, key: str) -> str:
        block = self.prompts.get(key) or {}
        return block.get(self.locale) or block.get("en") or ""

    def start(self) -> IvrResult:
        if not self.has_ivr:
            # Multicarding: no keypad journey at all. Saying so is more honest than inventing
            # a dialpad the flowchart does not have.
            self.finished = True
            return IvrResult("no_ivr", "offer", finished=True, accepted=None)
        return IvrResult("prompt", "offer")

    def press(self, key: str) -> IvrResult:
        if self.finished or not self.has_ivr:
            return IvrResult("no_ivr", None, finished=True, accepted=self.accepted)

        key = str(key).strip()
        self.attempts += 1
        self.keys.append(key)

        if key == self.accept_key:
            self.finished, self.accepted = True, True
            return IvrResult("accepted", "accepted", True, True, self.attempts, list(self.keys))
        if key == "2":
            self.finished, self.accepted = True, False
            return IvrResult("rejected", "rejected", True, False, self.attempts, list(self.keys))

        if self.attempts >= self.max_attempts:
            # invalid_key_behaviour: reprompt_once_then_advisor. A keypad loop that never
            # resolves is worse than handing the call to a person.
            self.finished, self.accepted = True, None
            return IvrResult("exhausted", "exhausted", True, None, self.attempts, list(self.keys))
        return IvrResult("invalid", "invalid", False, None, self.attempts, list(self.keys))

    def to_inbound(self) -> dict:
        """The `acceptance_result` field of handoff.yaml `inbound`, plus its evidence."""
        return {
            "mechanism": self.type,
            "operator": self.operator,
            "acceptance_result": ("accepted" if self.accepted
                                  else "rejected" if self.accepted is False else "no_response"),
            "attempts": self.attempts,
            # The keys pressed, not the meaning. A consent artefact is evidence of what the
            # customer did, and it is only worth anything if it records the raw action.
            "keys_pressed": list(self.keys),
            "simulated": True,       # never let this be mistaken for a real consent record
        }
