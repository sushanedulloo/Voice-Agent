# Technical Design Document
## SBI Card AI-BOT Outbound Voice Agent

| | |
|---|---|
| **Document** | TDD-VOICE-001 |
| **Version** | 0.1 — Draft |
| **Date** | 15 September 2026 |
| **Requirements** | `SRS.md` |
| **Diagrams** | `DIAGRAMS.md` |
| **Decisions** | `adr/` |

---

## 1. Design principles

Five principles, each traceable to a constraint rather than a preference.

1. **The model chooses; it does not speak.** Every customer-facing utterance resolves to approved,
   versioned content. The set of things the bot can say is a database table an auditor can read.
   (ADR-002)
2. **The partner owns the call.** We are a media endpoint, never an originator. This keeps the
   regulatory perimeter, the recording, and the call identity where they already are. (ADR-003)
3. **Measure before choosing.** No published benchmark covers 8 kHz Indic telephony audio. Component
   decisions come from our own corpus. (ADR-006)
4. **Optimise time-to-disqualify, not time-to-sell.** ~88% of contacts end in a no. That is where
   every rupee of saving lives.
5. **Instrumentation is a feature.** The engagement is won with a defensible cost-per-booked-SR
   number beside a human control arm — not with a demo. Logging is designed first, not retrofitted.

---

## 2. The turn loop

### 2.1 Latency budget

Target: **P50 ≤ 1000 ms, P95 ≤ 1800 ms** (NFR-101), customer end-of-speech to first bot audio.

| Stage | Budget | Notes |
|---|---|---|
| RTP in + jitter buffer | 40–80 ms | G.711 straight through, no transcode |
| VAD | ~1 ms | Silero, 8 kHz native (256-sample frames) |
| Turn detection | 15–160 ms | Model choice pending ADR-006 measurement |
| **Endpointing wait** | **300–500 ms** | **Dominates. This is where tuning pays.** |
| ASR finalisation | 150–300 ms | Overlaps endpointing — streaming ASR runs during speech |
| Routing | 16–100 ms | Embedding retrieval (ADR-004) |
| TTS time-to-first-byte | **0 ms cached** / 80–250 ms synthesised | Most turns are cache hits (ADR-005) |
| Playout buffer | 100–200 ms | |
| **P50 total** | **~900 ms – 1.1 s** | |

**Three things this table corrects from the earlier internal estimate.**

- The earlier budget claimed 900 ms at P95. That was wrong. The best published per-stage breakdown
  for a cascaded agent totals 934 ms *mean*; production systems measure P50 1.4–1.7 s, P95 3.3–3.8 s.
  Sub-second P95 over Indian PSTN is not achievable.
- **Endpointing, not the model, is the largest single cost.** Teams reach for a faster LLM when the
  win is in the silence threshold.
- Vendor latency claims run 1.5–5× optimistic because they measure inference only, excluding network
  and playout buffers. A widely-circulated per-stage table (STT 60–100 / LLM 100–180 / TTS 40–80)
  reconciles with no measured source and should be treated as fabricated.

### 2.2 Streaming, not request/response

ASR runs *during* customer speech, emitting partials. Only the tail after end-of-turn costs latency.
TTS streams from first byte. Nothing in the loop waits for a complete artefact before starting the
next stage.

### 2.3 Barge-in

Four steps, in order. Step 3 is the one teams miss and step 4 is a compliance control.

1. Cancel in-flight routing.
2. Cancel TTS synthesis mid-stream.
3. **Flush — meaning *drop*, not drain — the playout queue, transport buffer and SIP jitter buffer.**
   Voice gateways buffer 200–400 ms of audio for jitter resilience. Cancelling TTS alone leaves the
   bot talking for up to a second after the customer started. Target: audio stops within ~60 ms of
   the barge-in signal.
4. **Truncate conversation context to what the customer actually heard** (NFR-105). If the model
   generated a full disclosure sentence and the customer interrupted after four words, leaving the
   full sentence in context means the bot believes it disclosed terms the customer never heard. For
   a credit-product script that is mis-selling exposure, not a UX bug.

**Two failure modes specific to this deployment.**

*Acoustic echo → self-interruption.* The bot's own output leaks back through weak carrier echo
cancellation and it interrupts itself. Documented on real telephony carriers; likely on Indian
mobile networks. Detect by comparing interruption onset against playback position — speech that
begins exactly when we started talking is echo (FR-108).

*Backchannels.* "haan", "hmm", "achha", "ji", "theek hai" are conversational continuers, and Indian
speakers use them heavily. Treating them as interruptions makes the bot stutter; treating them as
agreement is worse. A per-language continuer list gates the barge-in trigger (FR-107).

---

## 3. Components

### 3.1 Media gateway
Stateful, one session per call leg. SIP UAS — we answer, never originate (ADR-003). Single-codec
answer: **PCMA/8000, ptime 20, RFC 4733 out-of-band DTMF**. Asserted explicitly in code; the A-law
/ μ-law confusion produces loud static that is still almost intelligible, and India is A-law.
No Opus on the carrier leg — it forces a transcode at their SBC for no benefit, and codec round
trips measurably degrade ASR.

### 3.2 Orchestrator
Stateless, horizontally scalable. Owns the dialog state machine, turn control, timers, barge-in
arbitration, and event emission. One process per call for crash isolation.

### 3.3 Speech-to-text
Streaming, Indic, 8 kHz native. **Engine selection deferred to the ADR-006 bake-off.** Requirement:
true streaming with partials — batch-only engines are disqualified regardless of accuracy.

### 3.4 Intent router
Embedding-first cascade with confidence banding and explicit out-of-scope rejection (ADR-004).
One-vs-rest sigmoid scoring, never softmax — softmax cannot express "none of these", and a confident
misroute on a rate question is mis-selling.

### 3.5 Text-to-speech and audio cache
Pre-rendered approved lines keyed on `(script_version, glossary_version, node, language, variant)`.
Runtime synthesis for variable spans only (ADR-005). Cache key includes content version so a stale
cache cannot play a superseded approved line.

### 3.6 Content store
Script nodes and FAQ glossary, versioned, loadable without deployment (NFR-401). BLC content changes
on a compliance cadence, not a sprint cadence.

---

## 4. Concurrency and scale

Requirement: 250 concurrent legs, headroom to 500 (NFR-201).

| Layer | Sizing | Basis |
|---|---|---|
| Media / SFU | Not the bottleneck | 3,010 audio participants on 16 cores at 80% CPU |
| Orchestrator workers | **~20 instances** at 4 cores / 8 GB | Published sizing 10–25 sessions/instance; size at ~15 + 20% headroom |
| ASR GPU | **5–8** with MPS + TensorRT; 20–30 naive | A single ASR request uses only 15–20% of an L40S's SMs by default |
| TTS GPU | Low duty cycle | Most audio is cached (ADR-005) |

> **The 4× GPU delta is engineering effort, and it is the single largest cost decision in the build.**
> MPS alone took one documented deployment from 16 GPUs to 4; adding TensorRT reached 2. Budget the
> work explicitly rather than discovering the bill.

**Autoscaling.** Do not scale on request count — sessions are multi-minute and HPA metrics propagate
too slowly. Scale on worker load with the autoscale trigger *below* the job-refusal threshold, so
capacity arrives before workers start declining calls. Asymmetric cooldowns: fast up, slow down.
Never burstable instances — CPU credit exhaustion stalls process spawn and times out turn detection.

**Outbound has an advantage over inbound here: we know when load arrives.** Pre-warm before each
campaign burst rather than reacting to it.

---

## 5. Data model

See `DIAGRAMS.md` §10. Three design points worth restating:

- **There is no customer entity.** `masked_ref_id` is the only customer key (CR-101).
- `script_version` and `glossary_version` are **stamped on the call**, not looked up live. A call must
  be reconstructable years later against the content approved at the time.
- `CONSENT_EVENT.consent_type` accepts both `verbal_agreement` and `ivr_keypress`, so open item OI-1
  resolves without a schema migration.

---

## 6. Failure handling

| Situation | Behaviour |
|---|---|
| Cannot understand | Re-prompt once; hand to a human on the third failure |
| Silence | Two re-prompts, then dispose and flag for re-churn |
| Out-of-scope question | Node's approved fallback, then route to human. Never an improvised answer |
| Stop request or abuse | Immediate safe exit, DNC flag, compliance event |
| Routing below confidence floor | Treat as out-of-scope. Uncertainty routes to a human, never to a guess |
| ASR unavailable | Fail the call to a human advisor; do not continue blind |
| Transfer endpoint fails | Play approved holding line, retry once, then dispose with an explicit failure code |
| System down | Dialer routes to human advisors as today (NFR-203). Degradation is to the existing process |

**Dead air is the worst failure.** When any stage misses its budget, speak an approved holding line
rather than going silent.

---

## 7. Observability

### Per turn
Correlation id (theirs), bot session id (ours), turn index, state node, transcript, **ASR confidence**,
detected intent, confidence band, utterance id played, content versions, and per-stage latency split.

ASR confidence per turn is the cheapest early warning that speech quality is degrading before it
corrupts routing.

### Metric design
**Set the objective on P99.9 of per-utterance round trip, not per-stage P95** (NFR-106). Three
independently healthy 95% stages compound to 85.7% joint success. Anchor one measurement per
utterance to avoid coordinated omission — per-frame sampling systematically undercounts slow events.

### Alert on
Dead-air rate (proxied by hang-ups, repeat questions, and literal "hello?" utterances), false
barge-in rate, missed-interruption rate, transfer success rate, and WER regression beyond 2 points
against baseline.

### Tracing
No voice-specific OpenTelemetry convention exists. Define a `voice.*` namespace now, aligned to
framework-native field names so dashboards port later. Span shape:
`call.lifecycle → turn.{n} → stt → eou → route → tts → playout`.

---

## 8. Evaluation

**Semantic WER over raw WER.** Weight meaning-changing errors — amounts, negations, product names —
above punctuation and fillers.

**LLM-as-judge has a specific, disqualifying blind spot for us.** In telecom transcripts, human
reviewers flagged safety issues **4–6× more often** than LLM judges, with missed escalation-to-human
the worst-detected class. Misstating a rate or fee is our direct analogue. **LLM judging is a first
pass at scale; human review is mandatory on anything safety-tagged.**

Script adherence targets: required-line delivery ≥99%, prohibited-response confirmed misses = 0,
identity-disclosure-before-pitch = 100%, evaluated on **every call, not sampled**.

Full approach in `TEST-STRATEGY.md`.

---

## 9. Security and deployment

India region only. Media in Mumbai — an RTP round trip to us-east-1 alone is ~250 ms and would make
the bot feel broken independent of everything else in §2.1.

Deployment topology in `DIAGRAMS.md` §12. Regulatory detail in `SECURITY-COMPLIANCE.md`.

---

## 10. Open design questions

| # | Question | Blocked by |
|---|---|---|
| 1 | Turn-detection model: Hindi accuracy is unpublished for every candidate | ADR-006 measurement |
| 2 | ASR engine and whether self-hosting is required from day one | ADR-006 + InfoSec (R-05) |
| 3 | Consent module shape | OI-1 |
| 4 | Router bootstrap data | OI-5 — we have not seen the glossary |
| 5 | Transfer mechanism: REFER to queue DID vs REST re-bridge | Partner ICD (ADR-003) |
