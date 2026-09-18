# SBI Card Outbound Voice Agent

A multilingual outbound voice agent that takes the **front ninety seconds** of SBI Card's
cross-sell calls: greet, pitch from a legally approved script, answer from an approved FAQ
glossary, detect interest, and warm-transfer interested customers to a human advisor.

We are a sub-vendor. The dialer, SIP trunk, advisors and CRM belong to SBI Card's calling
partner. We own the voice layer and the analytics around it.

> **Nothing here is approved content.** The default pack is TransOrg-invented placeholder
> standing in for the BLC script and the SBIC FAQ glossary, neither of which we have seen
> (OI-5). Every run prints its pack's provenance. See [Content packs](#content-packs).

---

## Quick start

```bash
python tools/validate_content.py          # prove the content pack is sound
python tests/test_engine.py               # the compliance invariants
python apps/repl.py flexipay en --trace    # talk to it in text
python apps/server.py                      # browser call console, real mic + voice
```

Then a whole campaign, end to end:

```bash
python tools/make_base.py --rows 2000      # synthetic calling base, no PII by construction
python apps/campaign.py --base runs/base.csv --concurrency 243
python tools/report.py --run <run-id>      # containment, adherence, cost per booked SR
```

---

## The one design idea

**The model never writes a sentence.** It returns an identifier — a script node id, a FAQ entry
id, or `OUT_OF_SCOPE` — and the runtime plays the approved string for that id (ADR-002).

Everything else follows. Audio can be pre-rendered because the utterance set is finite. The
audit trail is exact because every utterance is a known id. The ML problem shrinks from "generate
a safe answer about an interest rate" to "pick one of ~200 labels". And a bot that cannot compose
a sentence cannot invent a product claim on a recorded line at a bank.

There is no syntax in the content schema for a generative fallback. That is deliberate:
NeMo Guardrails' Colang falls through to an `llm continuation` flow that generates freely
(RESEARCH §2.1), and that hole is where this class of system fails.

## Layout

| Path | What |
|---|---|
| `content/` | The default content pack — everything the bot may say |
| `packs/` | Alternate packs (client-supplied, imported) |
| `engine/` | Runtime: content, router, machine, session, audit, ASR |
| `apps/` | REPL, browser call console, campaign runner |
| `tools/` | Validator, importer, benchmark, reports |
| `docs/` | SRS, DESIGN, RISKS, ADRs, RESEARCH |
| `cost_model.py` | Unit economics. Runnable. One place an assumption lives |

### Engine

```
content.py   load a pack, render lines, refuse to guess a missing variable
router.py    utterance -> identifier, with OUT_OF_SCOPE as a trained class
machine.py   the policy: which node, which disclosure, what may be said next
session.py   one call, assembling the handoff payload as it goes
audit.py     append-only turns.jsonl + calls.jsonl
asr_engines.py  IndicConformer on onnxruntime, no PyTorch
prerender.py    ADR-005 offline audio cache
```

The split is deliberate and is what every serious framework converges on (RESEARCH §2.1):
**LLM for dialogue understanding, deterministic engine for dialogue policy.** τ-bench measures
frontier function-calling agents below 25% on `pass^8`, with policy adherence degrading as
conversations lengthen — so the phase is tracked in code, not held in a prompt.

## Content packs

A pack is a directory. The runtime has no other source of customer-facing language, so replacing
the placeholder with SBIC's approved script is a directory swap:

```bash
python tools/validate_content.py --pack packs/sbic-blc-2026-10
python apps/campaign.py          --pack packs/sbic-blc-2026-10 --base runs/base.csv
python apps/server.py            --pack packs/sbic-blc-2026-10
```

`pack.yaml` declares `provenance` (`synthetic` or `blc-approved`) and an approval ref. Every
audit row carries a **SHA-256 of every byte of the pack**, so a transcript can always prove which
words were approved when that call happened — a version string is a claim, a hash is evidence.

When the client sends a spreadsheet:

```bash
python tools/import_script.py --in incoming/sbic --out packs/sbic-blc-2026-10 \
                              --name sbic-blc --approval-ref BLC-2026-1012
python tools/validate_content.py --pack packs/sbic-blc-2026-10
```

The importer keeps their text byte-for-byte — hand-copying an approved disclosure into YAML is a
chance to introduce a typo nobody would ever find. Our controls (intent vocabulary, disclosures,
out-of-scope corpus, global routes) carry across; they are engineering assets, not client content.

## The checks

`tools/validate_content.py` runs ten checks and a pack that fails does not load. There is no flag
to skip them. The ones that matter:

- **C5** — a node carrying `requires_disclosure` cannot be reached on **any** path without those
  disclosures having played. A must-analysis over the graph, not a spot check. This is the
  mechanical form of "disclosure before restricted topic".
- **C2** — every listening node can route `OUT_OF_SCOPE`, and that route ends at an approved line
  plus a human.
- **C10** — no literal digit outside a `{slot}`. Offer amounts are read from campaign variables,
  never written into a line.

`tests/test_engine.py` asserts the invariants that survive a content swap — a customer cannot be
dispositioned `AGREED` without terms having played; the canonical mis-sell (cash-advance rate
against a purchase-APR glossary) deflects; "wanted a human" is never counted as an agreement.

`tools/probe_router.py` measures routing quality on held-out utterances and **reports rather than
gates**. Leaks (off-glossary answered in scope) and over-deflects (in-scope sent to a human) are
reported separately, because a router that deflects everything scores zero leaks and is worthless.

## Speech

| | Status |
|---|---|
| **ASR, 8 Indian languages** | `ai4bharat/indic-conformer-600m` — MIT, ONNX, runs on CPU at RTF ~0.3, no PyTorch |
| **ASR, English** | Not covered by the above — its 22 languages are the scheduled Indian ones. Needs Whisper |
| **TTS** | `ai4bharat/indic-parler-tts` — Apache-2.0, build-time only (ADR-005) |
| **Browser console** | Web Speech API. A harness, not a component — 16 kHz, Google's servers, fails constraint 4 |

`python tools/fetch_models.py` fetches candidates and records licence + SHA per model. Every entry
reads `benchmarked_at_8khz: false`, and that only flips when `tools/benchmark_asr.py` has run
against real recordings.

**No model is selected.** Every published Indic STT number is measured at 16–24 kHz wideband;
telephony is 8 kHz, where word error roughly doubles. No public benchmark covers 8 kHz Indic
telephony, so the number that decides our choice does not exist and we have to produce it
(ADR-006). The benchmark's headline output is the **degradation column** — what each engine loses
over a phone line — which is the figure no vendor publishes.

⚠️ The mel front-end in `asr_engines.py` is reimplemented from NeMo's documented parameters,
because the shipped one is TorchScript and Windows Application Control blocks PyTorch on this
workstation. Feature extraction that is subtly wrong does not crash — it quietly costs accuracy.
Every engine carries `validated = False` until it is compared against `preprocessor.ts` on a
machine where torch runs.

## What is simulated, and labelled as such

```
base file (masked, no PII)
  -> dialer      connect rate, AMD                  [partner's - simulated]
  -> BOT         pitch, probe, agree, dispose       [ours - real]
  -> transfer    handoff payload                    [ours - real]
  -> advisor     verify, IVR or C2B, raise SR       [partner's - simulated]
  -> audit       append-only                        [ours - real]
  -> report      cost per booked SR vs human arm    [ours - real]
```

Every simulated rate is a named constant in `engine/advisor.py` or `apps/campaign.py`, and every
report prints the assumptions it used alongside the result. A cost-per-SR figure without its
assumptions beside it is not defensible, and this deal is decided by people who will ask.

## Constraints that are not negotiable

1. **The script is law.** The model selects an approved line. It never authors a product claim.
2. **The FAQ glossary is closed.** Off-glossary questions get the fallback line and a human.
3. **No PII in our systems.** The base is masked. Identity verification is the advisor's job.
4. **India-resident inference.** No foreign endpoint in the runtime path.
5. **Unbroken audit trail.** Every turn, consent event and disposition, append-only.

## Open items that block decisions

Full list in `docs/SRS.md §10`. The two that matter most:

- **R-14** — is a bot-answered call an "abandoned call" under TCCCPR 2(a)? Read literally that is
  ~88% of our traffic, at up to ₹10 lakh per violation. **Nothing dials until this is answered in
  writing.** It is answerable with two emails.
- **FlexiPay step 10a** — "customer is verified using their billing address PIN code and year of
  birth" names no actor. The identical step in Multicarding is explicitly the Ops advisor. If it
  is meant to be the bot, constraint 3 and that flowchart cannot both hold.
