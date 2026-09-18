# Technical Research Record
## SBI Card AI-BOT Outbound Voice Agent

| | |
|---|---|
| **Document** | RES-VOICE-001 |
| **Version** | 0.1 — in progress |
| **Date** | 15 September 2026 |
| **Purpose** | The evidence behind the decisions in `adr/`. Findings, not opinions, with sources. |

---

## How to read this

Source grading is applied throughout:

- 🟢 **Primary** — official documentation, standards body, peer-reviewed paper, or benchmark with disclosed methodology
- 🟡 **Secondary** — third-party measurement, source code, or reasoned technical argument
- 🔴 **Unverified** — vendor marketing or SEO content with no disclosed method

**Standing rule for this project: no component decision cites 🔴 as primary evidence.** Where only
🔴 sources exist, that is itself the finding, and it is stated as such.

### Research streams

| # | Stream | Status | Feeds |
|---|---|---|---|
| 1 | Voice agent architecture & orchestration | ✅ Complete | ADR-001, ADR-006, DESIGN §2–4 |
| 2 | Dialog management & guardrails | ✅ Complete | ADR-002, ADR-004, TEST-STRATEGY |
| 3 | Telephony & dialer integration | ✅ Complete | ADR-003, R-14, R-16, api/openapi.yaml |
| 4 | Indic speech stack | ⏳ Running | ADR-006, language strategy |
| 5 | India BFSI compliance & security | ⏳ Running | SECURITY-COMPLIANCE.md |
| 6 | Propensity & contact optimisation | ⏳ Running | FR-603, FR-706, the differentiation case |
| 7 | Call analytics, sentiment & STT audit | ⏳ Running | FR-701–FR-704 |

---

## 0. The finding that outranks the rest

**TCCCPR 2018 Regulation 2(a)** 🟢 ([full text](https://indiankanoon.org/doc/60694660/)):

> *"Abandoned Call means an outgoing call in which the sender does not connect the call to a live
> agent after the call is established and is answered by the recipient."*

Read literally, a call our bot answers, handles, and disposes without transferring to a human is an
abandoned call. That describes **~88% of our traffic** — exactly the containment on which the
entire savings case rests.

Regulation 4 prohibits auto-dialer use producing abandoned calls beyond limits set in the access
provider's Code of Practice. The 2025 second amendment sets penalties at ₹2/5/10 lakh escalating
per violation, 15-day suspension of outgoing service, and up to a year of telecom-resource
blacklisting.

**The counter-position**, which is defensible: the bot is an *Auto Dialer Call* under Reg 2(e) —
equipment that automatically initiates a call and then either plays a recorded message **or**
connects to a live person — placed to consented recipients with disclosed identity. But that
position must be held by the **Principal Entity on their DLT registration**, not asserted by a
sub-vendor.

**Correction to widely-repeated guidance.** The "3% abandoned calls over 24 hours" ceiling that
circulates in Indian contact-centre material is **Ofcom's, not TRAI's** 🟢
([Ofcom persistent misuse policy](https://www.ofcom.org.uk/phones-and-broadband/unwanted-calls-and-messages/persistent_misuse)),
and Ofcom has itself withdrawn it as a safe harbour. TCCCPR defers the number to the access
provider's Code of Practice. **Do not build to 3%.** Get the real number in writing.

→ `RISKS.md` R-14. Phase 0 of `DELIVERY-PLAN.md` exists because of this.

---

## 1. Voice agent architecture

### 1.1 The measurement gap

**No public benchmark covers 8 kHz telephony audio.** Every STT/TTS latency and accuracy figure in
circulation is measured at 16–24 kHz wideband.

| Finding | Source | Grade |
|---|---|---|
| A system at 5% WER on 16 kHz shows **12–18% at 8 kHz**; Hindi on AMR-NB production traffic "routinely exceeds 25–35%" | vendor research | 🔴 directionally corroborated below |
| GSM/2G codecs consistently degrade Indic ASR; 3G-narrowband and 4G-wideband stay near 16 kHz baseline. **Whisper-based models more noise-robust than Conformer-based** under background speech | [arXiv 2606.09335](https://arxiv.org/html/2606.09335) | 🟢 |
| Smart Turn v3 Indic accuracy: **Marathi 87.6%, Bengali 84.1%** — bottom tier. **No Hindi figure published.** v3.1 gains were English/Spanish only | [Smart Turn v3](https://www.daily.co/blog/announcing-smart-turn-v3-with-cpu-inference-in-just-12ms/), [v3.1](https://www.daily.co/blog/improved-accuracy-in-smart-turn-v3-1/) | 🟢 |
| LiveKit turn detector claims Hindi support — no accuracy figure published | [docs](https://docs.livekit.io/agents/build/turns/turn-detector/) | 🟢 |

**This is the origin of ADR-006.** We are outside the region where any published number applies.

### 1.2 Latency — what is actually measured

| Source | Measurement | Grade |
|---|---|---|
| Cascaded telecom voice agent, 500 utterances, per-stage timers: ASR 49 ms, LLM 670 ms, TTS 286 ms, TTFA 678 ms, **total 934 ms mean** (min 417, max 3154) | [arXiv 2508.04721](https://arxiv.org/html/2508.04721v1) | 🟡 best full breakdown found |
| FireRedChat: cascaded **900–1800 ms** end-to-end | [arXiv 2509.06502](https://arxiv.org/pdf/2509.06502) | 🟡 |
| LLM TTFT with realistic ~3.5k-token prompt: **P50 313–913 ms, P95 956–1964 ms**, 4,965 samples/model | [LiveKit benchmarks](https://livekit.com/benchmarks/latency) | 🟢 best independent methodology |
| Production reality across claimed 4M+ calls: **P50 1.4–1.7 s, P95 3.3–3.8 s, P99 8.4–15.3 s** | Hamming | 🔴 method undisclosed, but consistent with the above |
| ITU-T G.114: <150 ms one-way good, >400 ms unacceptable | G.114 | 🟢 standards body |

**Vendor claims run 1.5–5× optimistic.** Vapi markets "P50 <500 ms", independently measured at
720 ms P50 / 1050 ms P95 and 2.34 s P50 by two separate parties. Retell markets "~600 ms", measured
1.96 s P50.

⚠️ **A widely-circulated per-stage table (STT 60–100 / LLM 100–180 / TTS 40–80 / network 20–40 ms)
appears across a cluster of SEO sites and reconciles with no independently measured source.**
LiveKit's own benchmark puts LLM TTFT P50 alone at 313–913 ms. Treat that table as fabricated.

**Consequence:** NFR-101 was revised from "1000 ms P95" (not achievable) to "P50 ≤ 1 s, P95 ≤ 1.8 s".

Where sources flatly disagree and cannot be reconciled:
- Cartesia Sonic TTFB spans **7×** across sources: 40 ms (vendor, inference only) → 82 ms (vendor,
  "e2e") → 188–199 ms (third party) → 630 ms (competitor benchmark).
- Deepgram Nova-3: **247 ms** (Pipecat stt-benchmark, time-to-final-segment) vs **1422 ms** (Coval,
  median TTFT) — a 5.8× disagreement on the same product from different measurement anchors.

### 1.3 Turn-taking

The converged production stack: **noise suppression → VAD → min-speech-duration gate → semantic or
acoustic turn model**, with a hard silence fallback behind it. 🟡

| Component | Numbers | Grade |
|---|---|---|
| Silero VAD | 1.8 MB, **~1 ms per 30 ms chunk**, native 8 kHz (256-sample frames) | 🟢 [PyTorch hub](https://pytorch.org/hub/snakers4_silero-vad_vad/) |
| Smart Turn v3 | 8M params, **12.6 ms CPU** / 3.3 ms L40S, 23 languages, 8 MB | 🟢 |
| LiveKit turn detector v1-mini | **50–160 ms**, 14 languages **including Hindi**, ~396 MB resident | 🟢 |
| Fixed silence timeout | 800 ms "adds nearly a full second to every response" | 🟢 [LiveKit](https://livekit.com/blog/turn-detection-voice-agents-vad-endpointing-model-based-detection) |

The tradeoff in one line: Smart Turn is ~50× smaller and ~10× faster per inference but publishes no
Hindi number; LiveKit's detector supports Hindi explicitly but is a 396 MB model that changes the
per-worker memory footprint at 10–25 sessions/box.

**The code-switching failure mode nobody benchmarks:** speakers pause mid-utterance to switch
language, and that pause looks exactly like a turn-end to any model trained on monolingual data.
Expect to need `max_delay` above LiveKit's 2.5 s default.

### 1.4 Barge-in — where implementations break

Four steps required, in order. **Step 3 is the one teams miss; step 4 is a compliance control.**

1. Cancel in-flight generation
2. Cancel TTS synthesis mid-stream
3. **Flush — drop, not drain — playout queue, transport buffer, and SIP jitter buffer.** Gateways
   buffer 200–400 ms for jitter resilience; RTP playback delay is commonly 100–500 ms. Cancelling
   TTS alone leaves the bot talking for up to a second after the customer started. Target ~60 ms. 🟡
4. **Truncate context to audio actually played.** *"The LLM may have generated an entire sentence,
   but the user might only have heard half of it… the agent can later refer to something the user
   never actually heard."* 🟡 For a credit script this is mis-selling exposure, not a UX bug.

Two deployment-specific failure modes:

- **Acoustic echo → self-interruption.** Documented in production: the agent stopped mid-sentence on
  specific carriers because its own TTS leaked back through weak echo cancellation. Detect by
  comparing interruption onset against playback position. Likely on Indian mobile networks. 🟡
- **Backchannels.** "haan", "hmm", "achha", "ji" are continuers, not interruptions, and Indian
  speakers use them heavily. Deepgram Nova transcribes five vocalised signals explicitly so they can
  be filtered from the interruption trigger. An Indic continuer list is required. 🟢

⚠️ **Filler words distort your own metrics.** Full-Duplex-Bench-v3 measured an Ultravox-style system
using fillers on **88% of turns**, with a **47.9% interruption/overlap rate** and task completion
inflated to **8.4 s** despite excellent time-to-first-audio. 🟡
[arXiv 2604.04847](https://arxiv.org/pdf/2604.04847)

### 1.5 Orchestration frameworks

| Framework | Published sizing | Known production defects |
|---|---|---|
| **LiveKit Agents** | **4 cores / 8 GB → 10–25 concurrent jobs** 🟢; load test 30 agents at 3.8 cores / 2.8 GB. One OS process per job. SFU: 3,010 audio participants on 16 cores | Cgroup v2 CPU monitor flips worker to FULL on idle hosts → **lost calls** (#7102) 🟡; `load_threshold` is **not atomic** — two requests inside the 0.5 s window both accepted (#4884) 🟡 |
| **Pipecat** | No official per-session figure published | Cluster of races **all in the interruption path**: frames reordering causing 4+ duplicate responses (#1323), pipeline freeze on interrupt during LLM processing (#2567), dropped transcription frames (#5683) 🟡 |
| **jambonz** | FreeSWITCH-based, flat-fee self-host | Strongest pure-telephony feature set; BYO models |

**Selection leaning: LiveKit Agents self-hosted.** Only option with a first-party published sizing
number, process-level job isolation, and a tested-provider list that **includes Exotel and Plivo** —
both India-relevant. Pipecat is the better pipeline abstraction, but its defect cluster sits exactly
in the interruption path, which is the highest-risk path for a regulated outbound bot.

### 1.6 Scaling to 250 concurrent

| Layer | Sizing | Grade |
|---|---|---|
| SFU / media | Not a bottleneck at our scale | 🟢 |
| Agent workers | **~20 instances** at 4c/8GB, ~15 sessions each + headroom | 🟢 |
| ASR GPU naive | 20–30 L4/A10-class | 🟡 |
| **ASR GPU with MPS + TensorRT** | **5–8** | 🟢 |

> **A single ASR request uses only 15–20% of an L40S's SMs by default.** NVIDIA MPS took one
> documented deployment from **16 GPUs → 4** (75% cut); adding TensorRT reached **2** (88%).
> 🟢 [AWS ML blog](https://aws.amazon.com/blogs/machine-learning/reduce-asr-inference-costs-by-75-with-nvidia-mps-on-amazon-ec2/)
>
> **That 4× is engineering effort, not procurement.** It is the single largest cost decision in the
> build, and `cost_model.py` now carries a warning that its streams-per-GPU constants assume the
> MPS work is actually funded.

**Autoscaling.** Do not scale on request count — sessions are multi-minute, HPA metrics propagate in
30 s–3 min. Trigger autoscale *below* the job-refusal threshold so capacity arrives before workers
decline calls. Never burstable instances (t3/t4g): CPU credit exhaustion stalls process spawn and
times out turn detection. **Outbound's advantage: we know when load arrives — pre-warm before each
campaign burst rather than reacting.**

### 1.7 Observability

**Set the SLO on P99.9 of per-utterance round trip, not per-stage P95.** Three independently healthy
95% stages compound to **0.95³ = 85.7%** joint success. Avoid coordinated omission: anchor one
metric per *utterance*, not per audio frame, or slow events are undercounted. 🟡

**No voice-specific OpenTelemetry convention exists.** GenAI semantic conventions exited
experimental in early 2026 🟢, but STT/TTS/VAD/barge-in/SIP spans are unstandardised. Define a
`voice.*` namespace aligned to framework-native field names so dashboards port later.

**`stt.confidence` on every turn** is the cheapest early-warning signal that ASR is degrading before
it corrupts routing.

---

## 2. Dialog management and guardrails

### 2.1 The convergent pattern

Every serious framework has landed on the same split: **LLM for dialogue *understanding*,
deterministic engine for dialogue *policy*.**

| Framework | How it splits | Note |
|---|---|---|
| **Rasa CALM** | LLM emits structured *commands* (`start flow`, `set slot`, `cancel`); deterministic manager executes against YAML flows | *"By default, your assistant sends templated messages"* — generation is **off by default** 🟢 |
| **Pipecat Flows** | Graph of nodes; each node carries only its own prompt and relevant tools, collapsing the decision space | Voice-native, YAML/JSON declarative 🟢 |
| **NeMo Guardrails (Colang)** | Canonical intents matched by embedding similarity → **fixed bot strings** | ⚠️ unmatched utterances fall through to an `llm continuation` flow that **generates freely** — must be replaced with a hard deflection 🟢 |
| **Parlant** | Guidelines evaluated per turn + multi-turn journeys | Their docs say guidelines should specify *outcomes, not exact words* — **opposite of what we need** |

### 2.2 The measured argument against putting the script in a prompt

| Finding | Source |
|---|---|
| `pass^k` (all k trials succeed) — frontier function-calling agents **below 25% `pass^8`** on retail tasks, and **policy adherence degrades as conversation length increases** | 🟢 τ-bench, [arXiv 2406.12045](https://arxiv.org/abs/2406.12045) |
| Compliance degrades as dialogue lengthens **and when obligations shift between phases** — so track phase explicitly rather than assuming the model does | 🟢 INSURE-Dial, [arXiv 2602.18448](https://arxiv.org/pdf/2602.18448) |
| Rule-based restricts the LLM; prompt-driven doesn't enforce procedure. Introduces a benchmark for **out-of-workflow queries** — exactly "customer asks about rates mid-script" | 🟢 FlowAgent, [arXiv 2502.14345](https://arxiv.org/abs/2502.14345) |
| Expert script as the deterministic component, motivated explicitly by needing **inspectable decision paths for risk management** | 🟢 [arXiv 2412.15242](https://arxiv.org/abs/2412.15242) |
| **The counter-example.** Pure prompt-embedded business logic; author's own limitations concede *"non-deterministic nature… introduces risks of confabulations or deviations from prompt instructions"* and guardrails *"mitigate but complete elimination remains challenging."* Future work: compile down to a state machine | 🟢 Conversation Routines, [arXiv 2501.11613](https://arxiv.org/html/2501.11613v3) |

→ ADR-002.

### 2.3 Routing: measured tradeoffs

| Approach | Latency | Accuracy | Relative cost |
|---|---|---|---|
| Embedding retrieval (bi-encoder + ANN) | **16–100 ms** | 92–96% precision after example refinement | **~65× cheaper** than LLM |
| Fine-tuned small classifier (SetFit / ModernBERT) | 50–200 ms | F1 within 8–10% of frontier LLM; SetFit ~56× faster | negligible |
| LLM-as-router | **1–5 s** | best on compositional/ambiguous | ~$0.65 / 10k queries |

🟡 Published heuristic: <15 routes → LLM directly; 15–50 → embedding router; **50+ → fine-tuned
classifier; 100+ non-negotiable.** A hybrid cascade reports **within 2% of native LLM accuracy at
~50% less latency**.

**An LLM router on every turn is disqualifying on latency alone**, before cost. → ADR-004.

**When an LLM is called, constrain the decoding.** XGrammar (default structured-generation backend
in vLLM/SGLang/TensorRT-LLM) adds **<40 µs/token** 🟢. Outlines has documented schema-compilation
blowups (40 s–10 min) and scored lowest compliance on JSONSchemaBench. Asking a model politely for
a valid ID is not a control; logit masking is.

### 2.4 Out-of-scope rejection — the safety-critical part

**A router with no reject option will confidently misroute**, and *that misroute is mis-selling*.
Ask about cash-advance rates against a glossary holding a purchase-APR entry, and softmax returns
the purchase answer with high confidence — because softmax forces probability mass onto some class
by construction. It cannot express "none of these."

Required techniques 🟢:
- **One-vs-rest sigmoid, not softmax** ([arXiv 2405.19967](https://arxiv.org/pdf/2405.19967))
- Calibrated **per-class** rejection thresholds, tuned per language
- `OUT_OF_SCOPE` trained as an explicit class on real misrouted traffic
- Multi-boundary / multi-centroid learning — intents are not single blobs in embedding space
- Confidence banding: >0.8 auto, 0.5–0.8 answer + flag, <0.5 deflect

The deflection must be an **approved script line** plus a human route. Never a generated apology.

### 2.5 Guardrail frameworks in a real-time loop

Voice budget leaves roughly **50–100 ms** for an inline guardrail. Against that:

| Framework | Measured latency | Verdict |
|---|---|---|
| NeMo Guardrails | Vendor claims 100–300 ms; **independent study measured 0% bypass at >1.4 s mean, >4 s P95** 🟢 [arXiv 2605.06669](https://arxiv.org/pdf/2605.06669) | Dialog-rail *concept* yes; full stack inline, no |
| Guardrails AI | 50–200 ms per validation; regex near-zero, ML validators 100–200 ms | Only deterministic validators inline |
| Llama Guard | Heaviest | Async only |

⚠️ One widely-cited "I put 6 guardrail tools inline and measured latency" post **publishes no
p50/p95, no recall/precision, no dataset and no methodology** despite its headline. Its one durable
conclusion is architectural and correct: *cheap deterministic scanners inline, heavy model-based
ones async or sampled.*

**Verdict: do not adopt a guardrail framework as the primary control.** The closed-vocabulary
architecture *is* the control. Inline, keep only O(1) deterministic checks. Run NLI/LLM-judge
compliance scoring **async over every transcript** — which doubles as the audit artefact.

### 2.6 Evaluation

**Script adherence targets** 🟡 (published methodology): required-line delivery **≥99%**;
prohibited-response **zero confirmed misses**; disclosure-before-restricted-topic **≥98%**;
identity-before-disclosure **100%**; evaluated on **every call, not sampled**; evidence packet
completeness ≥99%; **every confirmed miss becomes a replayable CI test**.

**Simulation** 🟡: persona tiers (easy/medium/hard/adversarial), LLM judges calibrated against
50–100 human-reviewed calls until **>85% agreement** on binary metrics. Reported reality check:
**production failure rates run 20–30 points below pre-launch test results**, and combinatorics
explode (74 scenarios × 10 languages × 4 tiers × 3 versions = 8,880 runs).

**EVA-Bench** 🟢 [arXiv 2605.13841](https://arxiv.org/abs/2605.13841): 213 scenarios, splits task
accuracy from experience. Key result — **no evaluated system scores >0.5 on both simultaneously.**
Accuracy and naturalness trade off; a regulated product must choose accuracy and say so.

> ⚠️ **The LLM-judge blind spot that matters most to us.** 🟢
> [arXiv 2608.24314](https://arxiv.org/html/2608.24314): in telecom transcripts, **humans flagged
> safety issues 4–6× more often than LLM judges**, worst on missed escalation-to-human. Recovery
> turn count systematically underestimated (judge <1 vs human >3). Judge–human correlation is
> r>0.9 in retail but **much weaker in telecom**.
>
> Misstating an APR, fee or term is our direct analogue of that class. **LLM judging is a first pass
> at scale; human review is mandatory on anything safety-tagged.**

**Formal option:** AgentLTL ([arXiv 2607.02599](https://arxiv.org/pdf/2607.02599)) specifies
procedural constraints as Linear Temporal Logic over action traces — "disclosure before rate
discussion" is literally an LTL formula, checkable offline over every call. Heavier than we need on
day one; it is the rigorous version of the obligation matrix.

---

## 3. Telephony and dialer integration

### 3.1 Topology — the only sane choice

**The partner's dialer stays the B2BUA and master of the call. We are a media endpoint they dial.**
Every topology where we try to own the transfer fails on their SBC policy, their recorder, or their
CRM. → ADR-003.

| Topology | Verdict |
|---|---|
| **Dialer → INVITE → our media gateway** | **Recommended.** Their recorder, their CDR, their transfer. We answer and talk. |
| Dial-out-to-bot and bridge | Works; extra hop, more RTP latency |
| **SIPREC fork** (RFC 7865/7866) | **Listen-only.** No standard path to inject audio back. Useless for a talking bot |
| Media forking / RTP mirror | Same limitation |
| CPaaS media streaming | Fast to build, but inserts a second telco and collides with DLT numbering |
| **Bot as originator** | **Never.** Inherits DLT registration, CLI, DNCR, abandoned-call liability |

### 3.2 Warm transfer — what breaks

RFC 5589 🟢 defines three primitives: blind REFER, attended REFER with `Replaces`, and
conference/bridge. **The third is what actually ships**, because it does not depend on anyone
honouring REFER/Replaces and keeps a single mixing point for recording.

Failure modes 🟡:
- **REFER does not survive B2BUAs.** Their SBC terminates our dialog; the `Replaces` tuple refers to
  a dialog the far side never saw. Oracle and Ribbon SBCs variously proxy, reject, or convert REFER
  to a fresh INVITE 🟢 ([Oracle SBC docs](https://docs.oracle.com/en/industries/communications/session-border-controller/10.1.0/configuration/sip-refer-method-call-transfer.html))
- **We do not know advisor availability** — that lives in their ACD. Referring to a named advisor is
  wrong in principle
- **Recording continuity** — if the call re-anchors, the recorder starts a new session: two files,
  two IDs, broken audit trail
- Re-INVITE glare → `491 Request Pending`; RTP hairpinning → one-way audio after transfer

**The ask:** a transfer DID mapping to the advisor queue, or a REST endpoint on their dialer that
re-bridges their own leg. The latter is lowest-risk and is what Indian CCaaS stacks (Ozonetel,
Exotel) actually support.

### 3.3 Context passing, ranked by reliability

1. **CRM/CTI API + correlation key** — no size limit, no SBC to defeat. Write at *qualification*,
   not at transfer, so the screen-pop does not race it
2. **`User-to-User`** (RFC 7433 🟢) — standard, but **~128-byte practical ceiling.** Opaque token
   only, never a payload
3. **Custom `X-` headers** — SBCs strip unknown headers by default as topology hiding; platforms cap
   them (Genesys 10; Dynamics 5 × 256 chars 🟢)
4. **Whisper audio** — but costs the customer 3–6 s of dead air unless hold audio is played

**Pattern that works:** whisper audio + opaque UUI token + full payload pre-written to CRM keyed by
that token. Belt and braces, because any one of the three will be stripped by someone's SBC.

### 3.4 AMD

**Belongs on the partner's dialer**, before they hand us the leg — it is tied to *their* abandoned
call statistics, and running it ourselves costs detection latency after answer, in front of a live
human.

| Approach | Accuracy |
|---|---|
| Classic energy/cadence/beep | **60–85%**; beep detection measured at **50.7%**, fires 10–30 s in 🟢 [arXiv 2604.09675](https://arxiv.org/html/2604.09675v1) |
| Modern ML | **93–99%**; 96.1% combined, and over 77,000 production calls **0.3% FPR / 1.3% FNR** at **46 ms** on a dual-core CPU 🟢 |

Twilio's synchronous AMD costs **~2.4–4 s of silence** before the bot may speak 🟢. Two mitigations:
**overlap AMD with the greeting** (which is also the TRAI identity disclosure), converting the
latency into zero dead air; and treat **barge-in within ~800 ms as implicit human detection** —
cheaper and faster than any classifier.

### 3.5 Audio

| Setting | Value | Why |
|---|---|---|
| Codec | **PCMA/8000 (A-law)** | India. μ-law is North America/Japan. Getting it backwards produces loud static that is *still almost intelligible* — it survives a cursory smoke test 🟡 |
| ptime | 20 ms (160 samples) | |
| DTMF | RFC 4733/2833 **out-of-band** | In-band through ASR is garbage and won't survive transcoding |
| Opus on carrier leg | **No** | Forces transcode at their SBC; adds 20–40 ms and artifacts 🟢 |
| Jitter buffer | 40–60 ms adaptive | Every 10 ms is 10 ms added to barge-in response |
| Packet loss | 1–3% routine on Indian mobile | G.711 PLC is primitive; loss shows up directly as ASR errors |
| Media location | **Mumbai** | A round trip to us-east-1 alone is ~250 ms |

**Minimise codec hops.** A G.711→Opus→G.711 round trip is not neutral for ASR — models are trained
on particular codec artifacts.

### 3.6 Correlation across systems we do not own

**Adopt their ID; do not mint your own.** SIP `Call-ID` changes at every B2BUA hop, so it cannot be
the join key. Take the dialer's call identifier from the INVITE and make it our primary key; mint
`bot_session_id` as secondary; emit both on every log line and every CRM write.

**This is the whole trick** — an audit trail across systems you do not own is built by borrowing
their key, not by asking them to store yours.

RFC 7989 `Session-ID` 🟢 is the standards-track answer (two UUIDs designed to survive B2BUAs
unchanged). Ask; assume Indian deployments will not have it enabled.

**Also request a CDR feed.** Without it we cannot prove our own abandoned-call or transfer-success
numbers, and in the first dispute we are the party without data.

### 3.7 TCCCPR clause map

| Clause | Content |
|---|---|
| **Reg 2(a)** | Abandoned call definition — see §0 |
| **Reg 2(e)** | Auto Dialer Call: equipment initiating a call then playing a recording **or** connecting to a live person. Our bot sits squarely inside this |
| **Reg 4** | No auto-dialer producing silent/abandoned calls unless the originating access provider was notified in advance and limits are respected |
| **Schedule II §3** | Nine time bands; 00:00–06:00, 06:00–08:00, 08:00–10:00 and 21:00–24:00 **default OFF** → default permissive window **10:00–21:00**, not the "9–9" in secondary sources |
| **Schedule I §2(2)** | **140-series CLI for promotional** (credit-card cross-sell is promotional), 1600 for transactional. Routing must be segregated |
| **Reg 12(2), Sch I §4(4)** | Pre-checks and post-checks performed by the **Access Provider**. **We cannot legally scrub — we have no register access.** We receive an already-scrubbed list |
| **2025 amendment** | ₹2 / 5 / 10 lakh escalating penalties, 15-day outgoing suspension, up to 1 year blacklisting |

**Responsibility allocation:** DLT registration, CLI, scrubbing, time bands, abandoned-call ratio
and **voice script template registration** all sit with the Principal Entity / partner. Identity
disclosure in the bot's opening turn sits with **us**.

> **The hidden landmine:** the bot's utterances *are* the registered DLT script. A freely generating
> model emits unregistered script every call. This is an independent regulatory argument for
> ADR-002, separate from and stronger than the mis-selling one. → R-15.

---

## 4. Indic speech stack

⏳ *Research in progress.*

## 5. India BFSI compliance and security

⏳ *Research in progress. Will produce `SECURITY-COMPLIANCE.md`.*

## 6. Propensity and contact optimisation

⏳ *Research in progress. Feeds FR-603, FR-706 — the capability no competitor is offering and the
one SBI Card's own benefits slide asks for.*

## 7. Call analytics, sentiment and STT quality audit

⏳ *Research in progress. Feeds FR-701–FR-704 — charter features 2, 5 and 6.*
