#!/usr/bin/env python3
"""Text front-end. Type as the customer, watch the machine.

    python apps/repl.py                      # flexipay, en
    python apps/repl.py clip hi_latn
    python apps/repl.py flexipay en --trace   # show what the router almost picked

No audio, so no speech variables - which is the point. Every failure seen here is a dialogue
failure, not a transcription failure. Debug in that order.
"""

import sys
import json

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from engine import Content, Session                      # noqa: E402
from engine.machine import ComplianceError               # noqa: E402

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"


def speak(rec):
    for kind, ident, text, *_ in rec.spoke:
        tag = {"node": "BOT", "disclosure": "BOT*", "faq": "BOT?"}[kind]
        print(f"  {BOLD}{tag}{RESET} {text}  {DIM}[{ident}]{RESET}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    trace = "--trace" in sys.argv
    product = args[0] if args else "flexipay"
    locale = args[1] if len(args) > 1 else "en"

    content = Content()
    session = Session(content, product, content.example_campaign(), locale=locale)

    print(f"{DIM}{product} · {locale} · content v{session.machine.product.version} · "
          f"synthetic content, not BLC-approved{RESET}\n")
    speak(session.start())

    while not session.finished:
        try:
            said = input(f"\n  {BOLD}YOU{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not said:
            continue
        try:
            rec = session.say(said)
        except ComplianceError as exc:
            print(f"\n  COMPLIANCE STOP: {exc}")
            break
        print(f"  {DIM}-> {rec.route_kind}:{rec.route_id} "
              f"conf={rec.confidence} band={rec.band} {rec.engine_ms}ms{RESET}")
        if trace and rec.alternatives:
            for kind, ident, score in rec.alternatives:
                print(f"  {DIM}     {score:>6}  {kind}:{ident}{RESET}")
        speak(rec)

    print(f"\n{DIM}{'-' * 70}{RESET}")
    if session.finished:
        print(f"disposition: {BOLD}{session.machine.disposition}{RESET}")
    print(f"latency (engine only): {session.latency_summary()}")
    print("\nhandoff payload:")
    print(json.dumps(session.handoff_payload(), indent=2))


if __name__ == "__main__":
    main()
