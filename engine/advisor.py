"""The advisor leg. Simulated, because it belongs to the calling partner.

Everything here happens AFTER our transfer and is executed by someone else's people and
someone else's systems (CH-FLEXIPAY 10a/11a/12, CH-CLIP 11b/12a, CH-MULTICARD). We model it
for exactly one reason: without it the loop never closes, and the number the engagement is
judged on - cost per BOOKED SR - cannot be computed. A bot that reports transfers and not
outcomes is measuring its own activity.

Every rate below is an ASSUMPTION and none of them is ours to verify. They are named constants
so a client actual replaces them cleanly (CLAUDE.md), and every report that uses them prints
them alongside the result. A cost-per-SR figure quoted without these numbers beside it is not
defensible, and this engagement is decided by people who will ask.

Replace this module with the real CRM write-back when the ICD lands (DELIVERY-PLAN 0.8).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, asdict

# ---------------------------------------------------------------------------
# ASSUMPTIONS - all unverified, all replaceable
# ---------------------------------------------------------------------------

# Advisor re-verifies the customer (billing PIN code + year of birth). Some fail or refuse.
# OPEN: CH-FLEXIPAY step 10a names no actor for this. If it is meant to be the BOT, constraint 3
# is violated and our architecture is wrong. Asked, unanswered.
VERIFICATION_PASS_RATE = 0.88

# Of verified customers who agreed to the bot, how many still accept once an advisor walks them
# through the real terms. A bot "yes" is softer than a human "yes" - that gap is the single
# biggest threat to the business case and the first thing to measure against the control arm.
ACCEPTANCE_RATE = {"flexipay": 0.72, "clip": 0.81, "multicarding": 0.64}

# Of accepted offers, how many reach a created SR. Systems fail, sessions drop.
SR_CREATION_RATE = 0.96

# Advisor handle time, seconds, for the post-transfer leg only.
ADVISOR_SECONDS = {"flexipay": (150, 260), "clip": (110, 200), "multicarding": (190, 330)}

# An escalated transfer (asked for a human, or off-glossary) still consumes an advisor, and
# almost never books. Counting these as agreements is how a conversion rate gets inflated.
ESCALATED_ACCEPTANCE_RATE = 0.06
ESCALATED_SECONDS = (60, 180)


@dataclass
class AdvisorOutcome:
    advisor_disposition: str
    verification_result: str | None
    acceptance_result: str | None
    sr_number: str | None
    advisor_handle_time_ms: int
    mechanism: str


def assumptions() -> dict:
    return {
        "verification_pass_rate": VERIFICATION_PASS_RATE,
        "acceptance_rate": dict(ACCEPTANCE_RATE),
        "sr_creation_rate": SR_CREATION_RATE,
        "escalated_acceptance_rate": ESCALATED_ACCEPTANCE_RATE,
        "advisor_seconds": {k: list(v) for k, v in ADVISOR_SECONDS.items()},
        "source": "TransOrg estimates. None verified with the calling partner.",
    }


def mechanism_for(product: str) -> str:
    """CH-MULTICARD has no IVR - it uses a C2B link plus an OTP the customer enters."""
    return "c2b_link_otp" if product == "multicarding" else "ivr_dtmf"


def handle(payload: dict, rng: random.Random | None = None) -> AdvisorOutcome | None:
    """Run the advisor leg for one transferred call. Returns None if nothing was transferred."""
    rng = rng or random
    disposition = payload.get("disposition")
    product = payload["product"]
    mechanism = mechanism_for(product)

    if disposition not in ("AGREED_TRANSFERRED", "ESCALATED_TRANSFERRED"):
        return None

    if disposition == "ESCALATED_TRANSFERRED":
        secs = rng.uniform(*ESCALATED_SECONDS)
        if rng.random() < ESCALATED_ACCEPTANCE_RATE:
            return AdvisorOutcome("BOOKED", "pass", "accepted",
                                  f"SR{rng.randrange(10**7, 10**8)}",
                                  int(secs * 1000), mechanism)
        return AdvisorOutcome("HANDLED_NO_SALE", "pass", None, None,
                              int(secs * 1000), mechanism)

    secs = rng.uniform(*ADVISOR_SECONDS[product])

    if rng.random() > VERIFICATION_PASS_RATE:
        return AdvisorOutcome("VERIFICATION_FAILED", "fail", None, None,
                              int(secs * 0.45 * 1000), mechanism)

    if rng.random() > ACCEPTANCE_RATE[product]:
        return AdvisorOutcome("OFFER_REJECTED", "pass", "rejected", None,
                              int(secs * 1000), mechanism)

    if rng.random() > SR_CREATION_RATE:
        return AdvisorOutcome("SR_FAILED", "pass", "accepted", None,
                              int(secs * 1.15 * 1000), mechanism)

    return AdvisorOutcome("BOOKED", "pass", "accepted",
                          f"SR{rng.randrange(10**7, 10**8)}",
                          int(secs * 1000), mechanism)


def to_inbound(outcome: AdvisorOutcome) -> dict:
    """The `inbound` block of content/handoff.yaml. Note what is absent: the values used to
    verify. Pass or fail crosses back to us, never a PIN code or a year of birth."""
    return asdict(outcome)
