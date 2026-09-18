# Test Strategy
## SBI Card AI-BOT Outbound Voice Agent

| | |
|---|---|
| **Document** | TEST-VOICE-001 |
| **Version** | 0.1 |
| **Date** | 15 September 2026 |

---

## 1. What makes testing this different

A voice agent is non-deterministic, real-time, and in our case regulated. Three consequences shape
everything below.

**Pass rate is the wrong metric. Use `pass^k`.** The τ-bench methodology measures whether *all* k
trials succeed, not whether one did. Measured frontier agents fall below **25% `pass^8`** on retail
tasks — and policy adherence degrades further as conversations lengthen. A feature that works once
in a demo is not a feature that works.

**Pre-launch numbers lie.** Published experience puts production failure rates **20–30 percentage
points worse** than pre-launch test results. Plan for the gap rather than being surprised by it.

**Accuracy and experience trade off against each other.** EVA-Bench found **no evaluated system
scoring above 0.5 on both simultaneously.** A bot that is scrupulously correct feels stilted; a bot
that feels natural cuts corners. We must state which side we are choosing — for a regulated credit
product, correctness wins, and we should say so rather than pretend the tension does not exist.

---

## 2. Test levels

| Level | Scope | Cadence |
|---|---|---|
| **L0 — Unit** | Pure functions: numeric normalisation, state transitions, cache keys, disposition mapping | Every commit |
| **L1 — Component** | Each stage in isolation against fixtures: ASR on the corpus, router on labelled utterances, TTS cache resolution | Every commit |
| **L2 — Integration** | Orchestrator + real ASR/router/TTS, synthetic audio in, no telephony | Every commit |
| **L3 — Telephony** | Full SIP path against the partner's test trunk: codec, DTMF, transfer, barge-in | Nightly + pre-release |
| **L4 — Conversation** | Simulated end-to-end calls across personas and languages | Nightly (core), weekly (full) |
| **L5 — Compliance** | Script adherence and evidence packets over every call | Continuous, production |
| **L6 — UAT** | SBI Card BLC and Agency Ops on real calls | Phase gates |

---

## 3. The measurement corpus

**This is the foundation, and it is a dependency on the client** (ADR-006).

200–500 real recordings on the partner's actual carrier, in the actual languages, with real
code-mixing and real noise. Labelled for: transcript truth, intent truth, turn boundaries, and
numeric entities.

Used for the ASR bake-off, turn-detection tuning, router training and every regression run
thereafter. Reuse the `pipecat-ai/stt-benchmark` methodology rather than inventing one.

**Fallback if real audio is unavailable:** synthetic code-mixed speech through a G.711 A-law round
trip. Materially worse. Any decision made on it is flagged provisional.

---

## 4. Speech quality

**Semantic WER, not raw WER.** Weight errors that change meaning above those that do not.

| Error class | Weight | Why |
|---|---|---|
| Numeric entity (amount, tenure, rate) | **Critical** | Drives the offer. A misheard amount is mis-selling |
| Negation (*nahi* ↔ *haan*) | **Critical** | Inverts consent |
| Product name | High | Wrong product pitched |
| Intent-bearing content | High | Misroutes |
| Filler, punctuation, contraction | Ignore | No downstream effect |

**Reported per language, never aggregated** (FR-505). Malayalam, Kannada and Marathi typically lag
Hindi by a wide margin and an average hides it.

**Gates.** Numeric entity error rate > 5% blocks a language from going live. Overall semantic WER
regression > 2 points against baseline blocks release.

---

## 5. Conversation testing

### Persona simulation

Tiered by difficulty, per language:

| Tier | Characteristics |
|---|---|
| Easy | Clear speech, single language, cooperative, on-script responses |
| Medium | Accent variation, background noise, one objection, one FAQ |
| Hard | Heavy code-mixing, mid-utterance language switch, interruptions, off-script questions |
| Adversarial | Abuse, DNC demands, attempts to extract unapproved statements, silence, confusion, third party answering |

### Combinatorics are the trap

74 scenarios × 9 languages × 4 tiers × 3 model versions = **7,992 runs.** That does not fit in a
pre-deploy pipeline. Tier the cadence:

| Suite | Contents | When | Blocking |
|---|---|---|---|
| Core regression | Golden conversations, all languages, easy + medium | Every deploy | Yes |
| Extended | Full scenario matrix, hard tier | Nightly | No — reviewed daily |
| Adversarial | Abuse, extraction, safe-exit | Weekly + on content change | Yes for safe-exit |
| Production replay | Sampled real calls re-run against the new build | Weekly | Yes on regression |

---

## 6. Compliance testing

This is where a bank's evaluation is actually won or lost.

### Script obligation matrix

Every regulated obligation becomes a machine-checkable rule:

| Obligation | Rule | Target |
|---|---|---|
| Identity disclosure before pitch | Utterance A precedes utterance B | **100%** |
| Automated-agent disclosure in opening turn | Present in turn 1 | **100%** |
| Required line delivered | Exact or phrase-window match | **≥99%** |
| Prohibited response | Never emitted | **Zero confirmed misses** |
| Safe exit honoured within one turn | DNC → terminate | **100%** |
| Every utterance traceable to approved content | Utterance id ∈ approved set | **100%, by construction** |

The last row is free: ADR-002 makes it structural rather than statistical. That is the point of the
architecture.

### Evidence packet

Produced for **every call, not a sample**:

call id · correlation id · transcript span with timestamp · audio pointer · **script version +
glossary version + evaluator version** · rule id · rationale · reviewer decision · remediation status

Completeness target ≥99%. Under the RBI FREE-AI Assurance pillar we will be asked to reproduce a
specific call's decision path; that cannot be reconstructed retroactively.

**Every confirmed miss becomes a replayable regression test.** This is the loop that makes
compliance improve rather than merely be measured.

---

## 7. LLM-as-judge, and its specific blind spot

LLM judging is necessary for scale and **insufficient for safety.**

In telecom transcripts, human reviewers flagged safety issues **4–6× more often** than LLM judges.
The worst-detected class was missed escalation-to-human. Recovery turn count was systematically
underestimated — judges scored under 1 where humans scored over 3. Judge–human correlation is
r > 0.9 in retail but markedly weaker in telecom.

**Misstating a rate, fee or term is our direct analogue of that class.** So:

- LLM judge runs a first pass over 100% of calls.
- **Human review is mandatory on anything safety-tagged.** Non-negotiable.
- Judges are calibrated against 50–100 human-reviewed calls until agreement exceeds **85%** on
  binary metrics, and re-calibrated whenever the judge model changes.
- The judge model version is recorded in the evidence packet, because changing it changes the
  measurement.

---

## 8. Performance testing

| Test | Method | Gate |
|---|---|---|
| Turn latency | Per-utterance measurement on the corpus, P50/P95/P99.9 | P50 ≤ 1 s, P95 ≤ 1.8 s |
| Barge-in | Audio-level measurement of stop time | ≤ 200 ms |
| Context truncation on barge-in | Assert context matches audio actually played | 100% |
| Concurrency | Ramp to 250, hold, then to 500 | No job refusals, no latency cliff |
| Campaign burst | Cold start to 250 within 2 minutes | Pre-warm proves out |
| Soak | 8-hour calling window at steady load | No leak, no drift |

**Measure per utterance, one anchor per turn** (NFR-106). Frame-level sampling undercounts exactly
the slow events that matter.

---

## 9. What we are explicitly not testing

| Not tested | Why |
|---|---|
| The dialer, ACD, or CRM | Partner-owned. We test our side of the interface only. |
| DNCR scrubbing | Performed by the access provider before data reaches us. We cannot scrub; we have no register access. |
| Advisor behaviour after transfer | Out of scope, but *advisor handle time post-transfer* is measured as an outcome (R-13). |
| Booking and SR creation | SBI Card systems. |

---

## 10. Entry and exit criteria

**Entry to live POC dialling**
- Measurement corpus collected and baselined
- L0–L3 green; core regression green across Hindi and English
- Safe-exit adversarial suite at 100%
- Evidence packet pipeline producing complete packets
- **Written answers on R-14 (abandoned-call classification) and R-15 (DLT template coverage)**

**Exit from POC**
- Cost per booked SR measured against a human control arm on the same base, per product
- Script adherence ≥98% sampled, prohibited-response misses at zero
- Per-language speech quality reported separately
- All open items in `SRS.md` §10 either closed or explicitly accepted as risk
