# Delivery Plan
## SBI Card AI-BOT Outbound Voice Agent

| | |
|---|---|
| **Document** | PLAN-VOICE-001 |
| **Version** | 0.1 |
| **Date** | 15 September 2026 |
| **Supersedes** | The four-week roadmap in `Context.md` §10 |

---

## 1. What changed from the earlier roadmap

`Context.md` §10 sequenced four parallel workstreams to a Day-30 gate. That shape is right. Three
things have changed since it was written:

1. **Week 1 is now a measurement week, not a build week.** No published benchmark covers 8 kHz
   Indic telephony audio. Component choices must come from our own corpus (ADR-006).
2. **Two compliance questions now gate dialling**, not delivery. R-14 (is a bot-answered call an
   "abandoned call" under TCCCPR?) and R-15 (DLT template coverage) are answerable with emails and
   invalidate the business case if the literal reading holds.
3. **Lead with FlexiPay**, not CLIP. Its flow is the only one without an internal contradiction, and
   it is the ground where our strengths matter most.

---

## 2. Phase 0 — Unblock (now, before any build)

Not engineering work. It is on the critical path anyway, and it is cheap.

| # | Action | Owner | Blocks |
|---|---|---|---|
| 0.1 | **Written answer on abandoned-call classification** from the partner's compliance team and their access provider | Engagement lead | Everything. R-14 |
| 0.2 | **Confirmation that DLT script templates cover bot utterances** | Engagement lead | R-15 |
| 0.3 | **Request 200–500 real call recordings** + data-sharing agreement | Engagement lead | Week 1. ADR-006 |
| 0.4 | **Request the FAQ glossary** — entry count, shape, whether the bot may reason around it | SME call | OI-5, ADR-004 |
| 0.5 | **Resolve OI-1** — who conducts the CLIP consent IVR | SME call | Consent module, CLIP pricing |
| 0.6 | **Resolve OI-2** — FlexiPay gate: ticket size or record volume | SME call | Volume model |
| 0.7 | **Resolve OI-3** — 8 languages or 9 | SME call | Language scope |
| 0.8 | **Interface Control Document** with the calling partner | Engineering + partner | Week 2. ADR-003 |
| 0.9 | **Finance prices the run team** | Finance | Any external quote. R-07 |
| 0.10 | **Trace the commercial structure claim** (MSA, cost reimbursement) to its source | Engagement lead | Commercial model. OI-7 |

> **0.1 and 0.2 are not paperwork.** If a bot-handled, bot-disposed call counts as abandoned, ~88%
> of our traffic is a regulatory violation and the containment savings that justify the project
> disappear. Two emails now, or a discovery in month three.

---

## 3. Phase 1 — Measure (week 1)

**Deliverable: a number, not a demo.**

| Workstream | Output |
|---|---|
| Corpus | 200–500 real calls, labelled for transcript, intent, turn boundaries, numeric entities |
| ASR bake-off | Semantic WER per language per engine, on 8 kHz carrier audio. `pipecat-ai/stt-benchmark` methodology |
| Turn detection | False-cutoff and false-continue rates, measured specifically at code-switch boundaries |
| Latency harness | Per-stage, per-utterance measurement against a null dialog |
| Telephony | Test SIP leg up. Bot answers, hears audio, distinguishes human from machine |
| Compliance | Masked reference design, key vault, PII rejection at the boundary |

**Gate.** If turn latency P50 exceeds 1.1 s or numeric entity error rate exceeds 5% on the corpus,
stop and re-plan the stack. Finding this in week 1 is cheap; finding it in week 9 is not.

---

## 4. Phase 2 — Build FlexiPay (weeks 2–4)

One journey, two languages (Hindi, English). Not three journeys in nine languages.

### Week 2
- **Conversation.** Script as versioned config. State machine. Pre-render pipeline (ADR-005).
- **Integration.** Live transfer to a free advisor with whisper summary.
- **Data.** Turn logging end to end, including consent events and dispositions.
- **Compliance.** Consent artefacts stored with tamper evidence. Audit log locked against edits.

### Week 3
- **Conversation.** FAQ routing against the glossary. Confidence banding and out-of-scope rejection.
  Two objection loops. Barge-in with buffer flush and context truncation (NFR-105).
- **Integration.** CRM write-back over mutual TLS.
- **Data.** Funnel and cost-per-booking dashboards against the control-arm baseline.
- **Compliance.** Three-year archive with QA sampling running against it.

### Week 4
- **Conversation.** Sampled script-adherence check. Re-prompt variants. Indic backchannel list.
- **Integration.** Daily encrypted file ingest. Duplicate and DNC handling. Attempt tracking.
- **Data.** First best-time-to-call model on historical connect data. Propensity feature set.
- **Compliance.** India-hosting proof. Load test to 250 concurrent. InfoSec pack submitted.

---

## 5. The Day-30 gate

**Scope must be agreed in writing before this date is promised to anyone** (R-09).

| Criterion | Target |
|---|---|
| Live call, **FlexiPay, Hindi + English** | Turn latency P50 ≤ 1 s, P95 ≤ 1.8 s |
| Full journey | Campaign file in → warm transfer out → disposition in CRM |
| Script adherence | ≥ 98% sampled; prohibited-response misses zero |
| Safe exit | 100% on the adversarial suite |
| Concurrency | 250 concurrent legs sustained |
| Unit cost | Demonstrated ≤ ₹7.00 per contacted-minute equivalent |
| InfoSec | Pack submitted |

**Explicitly NOT in the Day-30 gate:** the other seven languages, Multicarding, CLIP, sentiment
analysis, the successful-call repository, or InfoSec *clearance* (as opposed to submission).

---

## 6. Phase 3 — Live POC (months 2–3)

The remaining two months of SBI Card's three-month evaluation.

- **Human control arm on the same base from day one.** Report differences, never levels. Without
  this the POC produces a working bot and no argument.
- Weekly script iteration from the successful-call repository.
- Language expansion: Tamil and Telugu next, then the remainder. **Nine shallow languages lose to
  two that work.**
- Add CLIP once OI-1 is resolved and the cost-per-booking machinery is proven.
- Best-time-to-call model switched on once there is enough data.
- Propensity-to-convert model on SBI Card's cross-sell history — the capability no competitor is
  offering, and the one their own benefits slide asks for.

**POC exit deliverable:** a defensible cost per booked SR, per product, measured against a human
control arm on the same base. Not a bot.

---

## 7. Sequencing rationale

**Why measurement before build.** The two things that can kill the economic case — latency on Indic
telephony audio and word error rate on code-mixed speech — are both cheap to discover in week 1.

**Why FlexiPay before CLIP.** CLIP is the full base worked by humans today, with a working baseline.
Winning there means beating a human process on conversion, judged against a control arm, in a
head-to-head where a competitor's better speech directly improves their number and ours stays flat.
FlexiPay's sub-₹10K segment gets no calls today — there is no baseline to lose against, every
booking is incremental revenue, and targeting precision matters more than speech quality. Every
rival will pitch CLIP because it is the biggest base.

**Why two languages before nine.** Depth in Hindi and English proves the architecture. Breadth
proves nothing if the depth is not there, and language work is the most parallelisable thing in the
plan — it can be added once the spine works.

---

## 8. Dependencies outside our control

| Dependency | On | Risk if late |
|---|---|---|
| Real call audio | SBI Card / partner | Week 1 runs on synthetic audio; every component decision becomes provisional |
| FAQ glossary | SBI Card BLC | Router cannot be trained. Week 3 slips |
| Test SIP trunk | Calling partner | Week 1 telephony slips; everything downstream compounds |
| CRM API spec | Calling partner | Week 3 write-back slips |
| Abandoned-call ruling | Access provider | **Dialling cannot start** |
| Seat cost and funnel actuals | Calling partner | Economic claims stay estimates |

**Six of these are on the client or partner side.** Phase 0 exists because the critical path runs
through other people's inboxes, and the only way to protect the timeline is to start those
conversations before the engineering needs the answers.
