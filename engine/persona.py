"""Simulated customers, so a call has two sides.

RESEARCH 2.6 prescribes persona tiers - easy, medium, hard, adversarial - and warns that
production failure rates run 20-30 points below pre-launch test results. So these exist to
produce a number we can watch move, not a number to quote. Anything measured here is an upper
bound on real performance and should be reported as one.

The personas speak TEXT. They sit above the speech layer entirely, which is deliberate: a
dialogue failure and a transcription failure are different bugs with different owners, and
mixing them is how teams spend a month tuning a prompt to fix an endpointing problem.

Every utterance below is HELD OUT - none of it appears in the pack's intent examples, FAQ
questions or out-of-scope corpus. A persona built from the router's own training examples
measures nothing except that the router can remember.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

# Outcome the persona is playing toward. Mix roughly mirrors the Phase-1 funnel assumption:
# ~88% of contacts end in a no. If that assumption is wrong the whole business case moves,
# so it lives here as a named constant rather than buried in a loop.
OUTCOME_MIX = {
    "not_interested": 0.62,
    "interested": 0.13,
    "callback": 0.09,
    "busy": 0.06,
    "wrong_person": 0.04,
    "dnc": 0.03,
    "silent": 0.02,
    "hostile": 0.01,
}

SAYS = {
    "confirm": ["speaking", "yes that is me", "haan main hi hoon", "yes who is this",
                "that's right", "ji haan boliye"],
    "interested": ["okay that sounds useful", "yeah I would like that",
                   "theek hai aage batao", "sounds alright, what next",
                   "haan mujhe interest hai", "fine, go ahead with it"],
    "not_interested": ["no thanks I am fine", "not required right now",
                       "mujhe filhaal nahi chahiye", "I am not looking for this",
                       "nahi bhai rehne do", "no I will manage"],
    "callback": ["call me after six", "kal subah call karo",
                 "not a good time, try tomorrow", "shaam ko baat karte hain"],
    "busy": ["I am in the middle of something", "abhi gaadi chala raha hoon",
             "can't talk now", "meeting chal rahi hai"],
    "wrong_person": ["you have the wrong number", "yeh number kisi aur ka hai",
                     "I don't hold that card", "galat number laga diya aapne"],
    "dnc": ["stop calling this number", "register me for do not disturb",
            "aage se call mat karna", "take me off your list please"],
    "hostile": ["why do you people keep calling", "this is a nuisance",
                "band karo yeh sab", "I am fed up of these calls"],
    "silent": [""],
}

# Questions a real person asks. Held out from the glossary wording on purpose.
QUESTIONS = {
    "flexipay": ["so how much would I pay every month", "kitna interest lagega is par",
                 "is there any extra charge on top", "how many months do I get",
                 "can I close it before time", "do I need to send any documents"],
    "clip": ["will this hurt my credit score", "kya isme koi charge lagega",
             "how long before the new limit shows", "can I ask for a smaller increase"],
    "multicarding": ["what does the card cost per year", "iska annual fee kitna hai",
                     "when would I get the card", "can I pick a different card"],
}

TRUST_PROBES = ["how do I know this is really SBI", "yeh fraud call toh nahi hai",
                "where did you get my number from", "are you a machine or a person"]

OFF_SCRIPT = ["what is the charge if I use this card in Dubai",
              "I need to change the address on my account",
              "mera reward points kitna hua hai",
              "someone used my card without telling me",
              "should I take this or put the money in an FD"]


@dataclass
class Persona:
    outcome: str
    tier: str                       # easy | medium | hard | adversarial
    questions: list = field(default_factory=list)
    turns_taken: int = 0
    max_turns: int = 12

    def reply(self, node_id: str, listening: bool) -> str | None:
        """What this customer says next, given where the bot is. None ends the call."""
        self.turns_taken += 1
        if self.turns_taken > self.max_turns or not listening:
            return None

        if node_id.startswith("N02"):
            if self.outcome == "wrong_person":
                return random.choice(SAYS["wrong_person"])
            if self.outcome == "silent":
                return ""
            return random.choice(SAYS["confirm"])

        if self.questions and random.random() < (0.75 if self.tier in ("hard", "adversarial")
                                                 else 0.35):
            return self.questions.pop(0)

        key = self.outcome if self.outcome in SAYS else "not_interested"
        return random.choice(SAYS[key])


def make(product: str, rng: random.Random | None = None) -> Persona:
    rng = rng or random
    roll, cumulative, outcome = rng.random(), 0.0, "not_interested"
    for name, share in OUTCOME_MIX.items():
        cumulative += share
        if roll <= cumulative:
            outcome = name
            break

    tier = rng.choices(["easy", "medium", "hard", "adversarial"],
                       weights=[0.40, 0.35, 0.20, 0.05])[0]

    questions = []
    pool = list(QUESTIONS.get(product, []))
    rng.shuffle(pool)
    questions += pool[:{"easy": 0, "medium": 1, "hard": 2, "adversarial": 2}[tier]]
    if tier in ("hard", "adversarial"):
        questions.append(rng.choice(TRUST_PROBES))
    if tier == "adversarial":
        questions.append(rng.choice(OFF_SCRIPT))
    rng.shuffle(questions)

    return Persona(outcome=outcome, tier=tier, questions=questions)
