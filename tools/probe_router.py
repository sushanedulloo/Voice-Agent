#!/usr/bin/env python3
"""Measure the router on utterances it has never seen. Reports, does not gate.

    python tools/probe_router.py

Deliberately NOT a test. tests/test_engine.py asserts invariants that must always hold; this
measures a quality that is currently poor and will be replaced. Mixing the two produces a suite
that gets weakened until it passes, which is how a compliance gate quietly stops gating.

The two error classes are not symmetric:

  LEAK      an off-glossary question got an in-scope answer.
            This is the mis-selling failure. RESEARCH 2.4. It must trend to zero.

  OVER-DEFLECT  an in-scope question went to a human unnecessarily.
            This costs an advisor minute. Annoying, not dangerous.

A router that deflects everything scores zero leaks and is worthless, so both are printed and
neither is optimised alone. The numbers below belong to the TF-IDF stand-in and are not
evidence about the production router - see engine/router.py.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from engine import Content                                  # noqa: E402
from engine.router import Router                            # noqa: E402

# Held out: none of these appear in intents.yaml, the FAQ files, or out_of_scope.yaml.
IN_SCOPE = [
    ("what interest will you charge me", "faq"),
    ("kitna byaaj lagega", "faq"),
    ("how many months can I spread it over", "faq"),
    ("do I have to give any papers", "faq"),
    ("is there a charge for closing it early", "faq"),
    ("yeah alright go ahead", "intent"),
    ("no I do not want this", "intent"),
    ("nahi mujhe nahi chahiye", "intent"),
    ("can you ring me tomorrow morning", "intent"),
    ("hold on I am driving right now", "intent"),
]

OFF_GLOSSARY = [
    "what is the rate on a cash withdrawal from an ATM",
    "do you offer two wheeler loans",
    "kya aap bike loan dete hain",
    "I want to add a nominee to my account",
    "my son wants an add-on card, what is the process",
    "what is the markup when I swipe abroad",
    "someone charged my card in Dubai and I was not there",
    "can you tell me my current outstanding",
    "I am going to complain to the RBI about this",
    "do you think I should take this offer or not",
    "what is the petrol surcharge waiver",
    "mera CIBIL score kitna hai",
]


def main():
    content = Content()
    router = Router(content)
    pitch = content.products["flexipay"].nodes["N04_PITCH"]

    print("IN-SCOPE  (want an in-scope id; a deflect here costs an advisor minute)")
    over = 0
    for text, want in IN_SCOPE:
        r = router.route(text, "flexipay", pitch)
        bad = r.kind == "out_of_scope"
        over += bad
        print(f"  {'DEFLECT' if bad else 'ok     '}  {text[:52]:54} -> "
              f"{r.kind}:{r.id} ({r.confidence}, {r.band})")

    print("\nOFF-GLOSSARY  (want out_of_scope; anything else is a LEAK)")
    leaks = 0
    for text in OFF_GLOSSARY:
        r = router.route(text, "flexipay", pitch)
        bad = r.kind != "out_of_scope"
        leaks += bad
        print(f"  {'LEAK   ' if bad else 'ok     '}  {text[:52]:54} -> "
              f"{r.kind}:{r.id} ({r.confidence}, {r.band})")

    print(f"\n  leaks          {leaks}/{len(OFF_GLOSSARY)}"
          f"   ({leaks / len(OFF_GLOSSARY):.0%})   <- the one that is mis-selling")
    print(f"  over-deflects  {over}/{len(IN_SCOPE)}"
          f"   ({over / len(IN_SCOPE):.0%})   <- the one that costs money")
    print("\n  TF-IDF stand-in. Not the production router, not calibrated, not evidence.")


if __name__ == "__main__":
    main()
