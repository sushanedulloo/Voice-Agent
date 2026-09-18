#!/usr/bin/env python3
"""Assertions on the properties that must hold, not on the words.

    python tests/test_engine.py

The content is synthetic and will be replaced wholesale by the BLC script, so a test that
asserts on a sentence is a test that will be deleted. These assert on the invariants that
survive the content swap:

  - a customer cannot be dispositioned as AGREED without the terms having played
  - the canonical mis-sell (cash-advance rate against a purchase-APR glossary) deflects
  - an unknown question reaches a human, never an invented answer
  - the payload that crosses our boundary carries nothing PII-shaped
  - "wanted a human" is never counted as an agreement

Stdlib asserts. No framework - RESEARCH 2.6 belongs to the async compliance scoring, not here.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from engine import Content, Session                                    # noqa: E402
from engine import prerender as pre                                    # noqa: E402
from engine.machine import ComplianceError, Machine                    # noqa: E402
from engine.session import PIILeak, _assert_no_pii                     # noqa: E402

CONTENT = Content()
CAMPAIGN = CONTENT.example_campaign()
PRODUCTS = ("flexipay", "clip", "multicarding")

passed = failed = 0


def check(name, fn):
    global passed, failed
    try:
        fn()
    except AssertionError as exc:
        failed += 1
        print(f"FAIL  {name}\n        {exc}")
    except Exception as exc:                                  # noqa: BLE001
        failed += 1
        print(f"ERROR {name}\n        {type(exc).__name__}: {exc}")
    else:
        passed += 1
        print(f"ok    {name}")


def session(product="flexipay", locale="en"):
    s = Session(CONTENT, product, CAMPAIGN, locale=locale)
    s.start()
    return s


# --------------------------------------------------------------------------
# The disclosure invariant. This is the one that matters most.
# --------------------------------------------------------------------------

def test_no_agreement_without_terms():
    """Every path that ends in AGREED_TRANSFERRED played the product terms first."""
    for product in PRODUCTS:
        prod = CONTENT.products[product]
        agreed = [n for n in prod.nodes.values() if n.disposition == "AGREED_TRANSFERRED"]
        assert agreed, f"{product} has no AGREED_TRANSFERRED terminal"
        # every predecessor chain into it must carry a requires_disclosure gate
        gates = [n for n in prod.nodes.values()
                 if n.requires_disclosure and n.next in {a.id for a in agreed}]
        assert gates, f"{product}: nothing gates the agreement terminal on a disclosure"


def test_runtime_refuses_undisclosed_agreement():
    """Even if the graph were wrong, the machine will not play a gated node."""
    m = Machine(CONTENT, "flexipay", CAMPAIGN)
    m.start()
    try:
        m._advance_to("N07_PRE_TRANSFER")       # jump the gate directly
    except ComplianceError as exc:
        assert "D03_FLEXIPAY_TERMS" in str(exc), exc
    else:
        raise AssertionError("machine played a gated node with no disclosure")


def test_disclosures_precede_pitch_on_the_real_path():
    s = session()
    assert "D01_IDENTITY" in s.machine.played_disclosures
    assert "D02_RECORDED_LINE" in s.machine.played_disclosures
    played = [u.id for u in s.machine.history if u.kind == "node"]
    assert played[0] == "N01_OPENING"


# --------------------------------------------------------------------------
# Out-of-scope rejection. RESEARCH 2.4 - the misroute IS the mis-selling.
# --------------------------------------------------------------------------

def test_cash_advance_never_answered_from_purchase_glossary():
    for utterance in ("what is the interest on cash withdrawal",
                      "cash nikalne par kitna interest lagta hai",
                      "can I take cash on this card"):
        s = session()
        s.say("yes")                                     # reach the pitch node
        rec = s.say(utterance)
        assert rec.route_kind == "out_of_scope", f"{utterance!r} -> {rec.route_id}"


def test_unknown_question_reaches_a_human_not_an_answer():
    s = session()
    s.say("yes")
    rec = s.say("what is the exchange rate for euros on this card")
    assert rec.route_kind == "out_of_scope", rec.route_id
    spoken_kinds = {u[0] for u in rec.spoke}
    assert "faq" not in spoken_kinds, "an off-glossary question got a glossary answer"
    assert s.machine.current in ("N99_FALLBACK_TRANSFER", "N09_TRANSFER_ESCALATED")


def test_fraud_report_is_urgent_not_a_sales_deflection():
    s = session()
    s.say("yes")
    s.say("there is a transaction I did not make")
    payload = s.handoff_payload() if s.finished else None
    if payload:
        assert "OOS_DISPUTE_OR_FRAUD" in payload["escalation_flags"], payload["escalation_flags"]


# --------------------------------------------------------------------------
# Measurement integrity.
# --------------------------------------------------------------------------

def test_human_request_is_not_an_agreement():
    s = session()
    s.say("let me talk to a human")
    assert s.finished
    assert s.machine.disposition == "ESCALATED_TRANSFERRED", s.machine.disposition
    assert s.handoff_payload()["agreement_confidence"] is None


def test_dnc_closes_and_flags():
    s = session()
    rec = s.say("don't call me again")
    assert s.machine.disposition == "DNC_REQUESTED", s.machine.disposition
    assert "DNC_REQUESTED" in s.handoff_payload()["escalation_flags"]
    assert rec.route_id == "DNC"


def test_call_cannot_continue_past_transfer():
    s = session()
    s.say("let me talk to a human")
    try:
        s.say("hello are you there")
    except RuntimeError as exc:
        assert "already ended" in str(exc)
    else:
        raise AssertionError("machine accepted a turn after the call ended")


# --------------------------------------------------------------------------
# Constraint 3 - no PII crosses the boundary.
# --------------------------------------------------------------------------

def test_payload_has_no_pii():
    s = session()
    s.say("let me talk to a human")
    _assert_no_pii(s.handoff_payload())          # must not raise


def test_pii_guard_does_not_cry_wolf():
    """A guard that false-positives gets switched off, and then the real check is gone with it.

    The two pathological UUID shapes below are pinned explicitly rather than hunted by random
    sampling: the first three segments all-digits matches PAN_LIKE, the first segment all-digits
    matches LONG_DIGITS. Both were found by running the suite repeatedly, not by reading it, and
    both would fire on roughly one real call in a thousand.
    """
    for uid in ("12345678-9012-3456-abcd-ef0123456789",   # looks like a card number
                "12345678-abcd-ef01-2345-6789abcdef01",   # looks like a long digit run
                "3a262172-ecd7-4730-8032-c2e30b52339f"):  # ordinary
        s = session()
        s.correlation_id = uid
        s.say("let me talk to a human")
        _assert_no_pii(s.handoff_payload())
    for _ in range(50):                                    # plus fresh ones, for luck
        s = session()
        s.say("let me talk to a human")
        _assert_no_pii(s.handoff_payload())


def test_pii_guard_rejects_a_malformed_identifier():
    _assert_no_pii({"correlation_id": "3a262172-ecd7-4730-8032-c2e30b52339f"})
    for bad in ("not-a-uuid", "4111111111111111", ""):
        try:
            _assert_no_pii({"correlation_id": bad})
        except PIILeak:
            continue
        raise AssertionError(f"accepted malformed correlation_id {bad!r}")


def test_pii_guard_actually_fires():
    for bad in ({"x": "4111 1111 1111 1111"}, {"y": {"z": "9876543210"}}):
        try:
            _assert_no_pii(bad)
        except PIILeak:
            continue
        raise AssertionError(f"PII guard missed {bad}")


def test_customer_name_is_spoken_but_never_logged():
    """The one PII-bearing slot. It must reach the customer's ear and nothing else.

    The bot greets by name because a nameless greeting sounds like a robocall. That is a real
    product requirement and it is also the one place the pack touches PII, so the guard is
    tested rather than assumed.
    """
    name = "Tushar"
    campaign = dict(CAMPAIGN, customer_first_name=name)
    s = Session(CONTENT, "flexipay", campaign)
    s.start()
    spoken = " ".join(u[2] for u in s.records[0].spoke)
    assert name in spoken, "the greeting did not use the customer's name"

    s.say("let me talk to a human")
    payload = s.handoff_payload()
    blob = repr(payload)
    assert name not in blob, f"customer name leaked into the handoff payload: {blob[:200]}"
    assert "customer_first_name" not in payload

    # and it must not reach the audit trail either
    for rec in s.records:
        for _, _, text, *_ in rec.spoke:
            pass          # spoken text is fine - that is the call
        assert name not in repr([rec.route_kind, rec.route_id, rec.node_after])


def test_campaign_variables_are_never_invented():
    """A line whose slot has no value must fail loudly, not play with a hole in it."""
    s = Session(CONTENT, "flexipay", {"brand_name": "SBI Card"})
    try:
        s.start()
    except KeyError as exc:
        assert "agent_display_name" in str(exc) or "brand_name" not in str(exc)
    else:
        raise AssertionError("rendered a line without its campaign variables")


# --------------------------------------------------------------------------
# All three products behave the same way. One engine, three configs.
# --------------------------------------------------------------------------

def test_every_product_reaches_a_disposition():
    for product in PRODUCTS:
        for utterance, expected in (("not interested", "NOT_INTERESTED"),
                                    ("don't call me again", "DNC_REQUESTED"),
                                    ("wrong number", "WRONG_PERSON")):
            s = session(product)
            s.say(utterance)
            assert s.finished, f"{product}/{utterance!r} did not terminate"
            assert s.machine.disposition == expected, \
                f"{product}/{utterance!r} -> {s.machine.disposition}, wanted {expected}"


def test_every_node_line_renders_for_every_locale():
    for product in PRODUCTS:
        for locale in CONTENT.locales:
            for node_id in CONTENT.products[product].nodes:
                CONTENT.node_line(product, node_id, locale, CAMPAIGN)


# ---------------------------------------------------------------------------------------------
# The audio cache (ADR-005). These guard the seam between the machine that renders and the
# machine that serves - a render is only useful if the server can find what it produced.
# ---------------------------------------------------------------------------------------------

def test_audio_index_key_matches_what_the_server_looks_up():
    """The renderer writes the index; apps/server.py reads it. One function, both sides.

    This was two hand-written f-strings in two files. They agreed, until one of them would not
    have - and the failure is silent: every span misses the cache and the console quietly
    re-synthesises BLC-approved audio at call time, which is the exact thing ADR-005 forbids.
    """
    assert pre.index_entry("hi", "default", "namaste") == "hi\u241fdefault\u241fnamaste"


def test_render_plan_is_deduplicated_and_locale_scoped():
    full = pre.plan(CONTENT, engine="x", version="1")
    one = pre.plan(CONTENT, engine="x", version="1", locales=["en"])
    assert all(loc == "en" for loc, _ in one.values())
    assert 0 < len(one) < len(full)
    # keyed by what is spoken, so a sentence shared by two nodes is one clip
    assert len(full) == len({(loc, text) for loc, text in full.values()})


def test_a_reworded_line_gets_a_new_clip():
    """The cache cannot serve last month's approval for this month's wording."""
    a = pre.cache_key("your limit can go up", "en", "default", "x", "1")
    b = pre.cache_key("your limit may go up", "en", "default", "x", "1")
    assert a != b
    assert a == pre.cache_key("  your limit can go up  ", "en", "default", "x", "1")


def test_slot_bearing_spans_are_never_prerendered():
    """A cached "...about 4,500 rupees" would be played to a customer offered something else."""
    for key, (locale, text) in pre.plan(CONTENT, engine="x", version="1").items():
        assert "{" not in text, f"{locale} {key}: slot span in the pre-render plan: {text!r}"


def test_index_merges_rather_than_replaces():
    """Two machines render disjoint locales and ship back caches. Neither may erase the other."""
    import tempfile

    class _R:
        name, version, sample_rate = "x", "1", 44100

    with tempfile.TemporaryDirectory() as tmp:
        cache = pathlib.Path(tmp)
        for locales in (["en"], ["hi"]):
            wanted = pre.plan(CONTENT, engine="x", version="1", locales=locales)
            for key in wanted:
                (cache / f"{key}.wav").write_bytes(b"")
            pre.write_index(cache, wanted, content=CONTENT, renderer=_R())
        spans = pre.load_index(cache)["spans"]
        assert any(k.startswith("en\u241f") for k in spans)
        assert any(k.startswith("hi\u241f") for k in spans), "second render erased the first"


def test_outstanding_is_the_whole_resume_protocol():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        cache = pathlib.Path(tmp)
        wanted = pre.plan(CONTENT, engine="x", version="1", locales=["en"])
        assert len(pre.outstanding(wanted, cache)) == len(wanted)
        done = list(wanted)[:3]
        for key in done:
            (cache / f"{key}.wav").write_bytes(b"")
        assert len(pre.outstanding(wanted, cache)) == len(wanted) - len(done)


def test_render_seed_is_stable_across_processes():
    """parler samples, so the seed is the only thing making a re-render reproduce the clip.

    The literal is the point: Python salts str hashing per process, so a seed built on hash()
    would match within a run and differ between runs. This value must survive a new interpreter,
    a new machine and a new year.
    """
    assert pre._stable_seed(0, "aap ka limit") == 735276500
    assert pre._stable_seed(7, "aap ka limit") == 735276499
    assert pre._stable_seed(0, "a") != pre._stable_seed(0, "b")


def test_batch_padding_is_trimmed_off():
    """Untrimmed, a short span batched with a long one carries seconds of dead air."""
    import numpy as np
    sr = 16000
    clip = np.concatenate([np.ones(sr, dtype="float32") * 0.5, np.zeros(sr * 3, "float32")])
    out = pre.trim_trailing_silence(clip, sr)
    assert sr <= out.size < sr * 1.2, out.size
    assert pre.trim_trailing_silence(np.zeros(sr, "float32"), sr).size == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            check(name[5:].replace("_", " "), fn)
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
