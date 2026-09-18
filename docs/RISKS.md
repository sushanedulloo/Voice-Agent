# Risk Register
## SBI Card AI-BOT Outbound Voice Agent

| | |
|---|---|
| **Document** | RISK-VOICE-001 |
| **Version** | 0.1 |
| **Date** | 15 September 2026 |
| **Review cadence** | Weekly during POC; at every phase gate thereafter |

---

## Scoring

**Probability** — L (≤20%), M (20–60%), H (>60%)
**Impact** — 1 Cosmetic · 2 Recoverable · 3 Milestone slip · 4 Commercially serious · 5 Deal-ending

**Score** = P × I where L=1, M=2, H=3. Anything scoring ≥ 8 is escalated to the engagement lead
weekly. Anything with Impact 5 is escalated regardless of probability.

---

## 1. Register

### R-01 · Latency on Indic telephony audio
**P** M · **I** 4 · **Score 8** · *Engineering*

Every 100 ms across six turns is billed time and degrades conversation quality. If we cannot hold
turn latency under one second on 8 kHz Indic audio, the 50-second target dies and with it the
entire cost case. End-of-turn detection, not the model, is usually the bottleneck.

**Mitigation.** Build the latency harness in week 1, before any dialog logic exists. Measure per
stage, not end to end. Treat NFR-101 as a gate, not a goal.
**Trigger.** P95 turn latency > 1.1 s on the week-1 harness.
**Fallback.** Increase pre-rendered audio share; shift more turns to deterministic playback with
no model call in the loop.

---

### R-02 · Code-mixing and spoken amounts break transcription
**P** H · **I** 4 · **Score 12** · *Engineering*

"Mera limit increase kar do", "pachaas hazaar", "point five lakh" — real Indian phone speech is
code-mixed and numerically ambiguous. A clean monolingual Hindi word error rate proves nothing.
Misheard amounts in a credit conversation are a mis-selling exposure, not just a quality issue.

**Mitigation.** Score the week-1 ASR bake-off specifically on code-mixed utterances and spoken
amounts, on real card-call audio. Build a domain lexicon and numeric normaliser before dialog
logic. Never let a transcribed amount drive an utterance — offer values come from campaign
variables only (FR-202).
**Trigger.** Numeric entity error rate > 5% on the code-mixed test set.

---

### R-03 · Conversion drop versus the human control arm
**P** M · **I** 5 · **Score 10** · *Commercial*

If the bot converts more than ~25% worse than an advisor, no price gets us to a cheaper booking.
The invoice shrinks and the cost per sale rises.

**Mitigation.** Human control arm running the same base from day one of the live POC. Report
*differences*, never levels. Make cost per booked SR the headline metric in every report.
**Trigger.** Bot agreement rate below 8 per 100 conversations sustained over two weeks.
**Fallback.** Retreat to the FlexiPay sub-₹10K segment where there is no human baseline to lose
against, and reframe as incremental revenue.

---

### R-04 · Consent scope is larger than we assumed
**P** M · **I** 5 · **Score 10** · *Compliance* · **Open item OI-1**

SBI Card's RACI makes the BOT Engine **Responsible** for Consent Capture. Their process map says
the bot runs the CLIP IVR. Their CLIP flowchart says the advisor does. If the bot genuinely
captures the binding consent artefact, we move inside the regulated consent chain: heavier
InfoSec posture, legal-artefact custody, and a materially longer CLIP call.

**Mitigation.** Resolve at the clarification call before architecture is frozen. Design the
consent module behind an interface so either answer is implementable. Price CLIP separately.
**Trigger.** Client confirms bot-run IVR.
**Impact if triggered.** CLIP loaded cost moves ₹2.26 → ~₹2.86 per conversation; margin at ₹4.75
falls 52% → 40%. Still viable, but one price across three products stops working.

---

### R-05 · Data residency forces full on-premise deployment
**P** M · **I** 4 · **Score 8** · *Compliance*

If InfoSec requires inference inside the calling partner's infrastructure rather than an India
region cloud, both the cost stack and the timeline move. Managed APIs become unavailable and we
self-host from day one — which is cheaper at scale but far slower to stand up.

**Mitigation.** Assume India-resident from the start. Keep the model layer behind an interface so
managed and self-hosted are swappable. Budget for self-hosted GPU capacity in the fixed base.
**Trigger.** InfoSec review rejects India-region managed endpoints.

---

### R-06 · Route to market — the partner white-labels a competitor
**P** M · **I** 5 · **Score 10** · *Commercial*

DialNexa offers white-label to agencies. The calling partner could resell a competitor under
their own name and the bake-off never happens. We would lose without being evaluated. This is a
relationship risk, not a product risk, and it is the one our engineering cannot fix.

**Mitigation.** Get to the calling partner early and directly, not only to SBI Card. We contract
with the agency, so the agency is the actual buyer.
**Owner.** Engagement lead, not engineering.

---

### R-07 · Fixed-cost base is an estimate, not a costed plan
**P** H · **I** 3 · **Score 9** · *Commercial*

The floor price rests on a ~₹30 lakh monthly fixed base built from our own headcount assumptions.
At Phase-1 volume fixed cost is ₹1.45 of a ₹1.67 unit cost — it is almost the entire number. A
30% error in the run team moves the floor materially.

**Mitigation.** Finance prices the run team before any external quote. Until then, quote only
ranges externally.
**Trigger.** Any client-facing price commitment before finance sign-off.

---

### R-08 · POC volume is too small to be profitable at any price
**P** H · **I** 2 · **Score 6** · *Commercial*

At 3 lakh conversations a month our loaded cost is ~₹10 per conversation against a target price
near ₹4.75. The POC is structurally loss-making. This is normal and expected — but only if it is
a deliberate, budgeted investment rather than a discovery made mid-engagement.

**Mitigation.** Book the POC as customer-acquisition cost (₹18–25 lakh over three months against
a ~₹14 crore annual contract). Never price the POC to be profitable; price it to win.

---

### R-09 · Timeline promise outruns scope
**P** H · **I** 3 · **Score 9** · *Delivery*

"Four weeks to a working product" holds for one journey in two languages. It does not hold for
three journeys across nine languages with InfoSec clearance. The gap between those two readings
is where client relationships break.

**Mitigation.** Put the scope of the Day-30 gate in writing before it is promised. SRS §8.1 states
it; get it countersigned.
**Trigger.** Any external communication of a date without an attached scope.

---

### R-10 · Media streaming is metered by the partner
**P** M · **I** 3 · **Score 6** · *Commercial* · **Open item OI-4**

We model telephony at zero because the partner owns the trunk. Indian providers commonly charge
separately to fork RTP to a third party — roughly ₹0.15/min, which exceeds our entire model cost
stack.

**Mitigation.** Get it in writing before quoting. Treat as a pass-through line item if confirmed.

---

### R-11 · FAQ glossary is larger or more open-ended than assumed
**P** M · **I** 3 · **Score 6** · *Engineering* · **Open item OI-5**

Our guardrail architecture assumes a finite, approved, select-don't-generate answer set. If SBI
Card expects genuinely open-ended Q&A about a credit product, the compliance design and the cost
model both change.

**Mitigation.** Request the glossary at the clarification call. Design the answer layer as
retrieval-over-approved-content so it scales from 50 to 500 entries without redesign.
**Note.** We have not seen the glossary. Everything in ADR-002 assumes its shape.

---

### R-12 · Competing on the wrong axis
**P** M · **I** 4 · **Score 8** · *Commercial*

Gnani owns its model stack and is measurably better on Indic telephony audio. If the evaluation
becomes a speech-quality bake-off or a rate auction, we lose. Our own deck currently presents
900 ms turn latency as a strength against a competitor claiming sub-200 ms.

**Mitigation.** Remove latency from the pitch. Compete on who to call, when, how many attempts
are worth buying, and provable cost per booked SR against a control arm. Do not fight on speech.

---

### R-14 · A bot-answered call may legally be an "abandoned call"
**P** M · **I** 5 · **Score 10** · *Compliance* · **NEW — highest-consequence open question in the project**

TCCCPR 2018 Regulation 2(a) defines an abandoned call as *"an outgoing call in which the sender
does not connect the call to a live agent after the call is established and is answered by the
recipient."*

Read literally, **every call our bot handles and disposes without transferring to a human is an
abandoned call** — which is ~88% of them. Regulation 4 prohibits auto-dialer use producing
abandoned calls beyond limits set in the access provider's Code of Practice, and the 2025 second
amendment carries penalties of ₹2/5/10 lakh escalating per violation, 15-day suspension of
outgoing service, and up to a year of telecom-resource blacklisting.

The defensible counter-position is that the bot is an *auto dialer call* under Reg 2(e) — equipment
that connects to a recorded message *or* a live person — with disclosed identity, to consented
recipients. But that position must be taken by the **Principal Entity on their DLT registration**,
not asserted by us.

Note also: the widely-quoted "3% abandoned call" ceiling is **Ofcom's, not TRAI's**, and Ofcom has
itself withdrawn it as a safe harbour. TCCCPR defers the number to the access provider's Code of
Practice. Do not build to 3% on the strength of a vendor blog.

**Mitigation.** Put the question to the partner's compliance team and their access provider **in
writing, before the POC dials a single number.** Obtain (a) the actual abandoned-call limit from
their COP, (b) written confirmation of how a bot-handled, bot-disposed call is classified.
**Trigger.** Any dialling before that confirmation exists.
**If the literal reading holds.** The economics invert entirely: the bot would have to transfer
nearly every call, which destroys the containment savings that justify the project. This is not an
engineering risk — it is an existence risk, and it is cheap to resolve now and ruinous to discover
in month three.

---

### R-15 · Bot utterances are unregistered DLT script content
**P** M · **I** 4 · **Score 8** · *Compliance*

Under TCCCPR, commercial voice scripts are registered as templates on the DLT platform by the
Principal Entity. The bot's spoken content *is* that script. A model that generates novel phrasing
emits unregistered script on every call.

**Mitigation.** This is an independent regulatory argument for the closed-vocabulary architecture
in ADR-002 — separate from, and stronger than, the mis-selling argument. Every utterance resolves
to an approved, registered line. Log the rendered utterance id on every turn so template coverage
is auditable.
**Note.** This makes FR-203 a *regulatory* requirement, not merely a quality one.

---

### R-16 · Warm transfer fails at the partner's SBC
**P** H · **I** 3 · **Score 9** · *Engineering*

SIP REFER does not reliably survive a B2BUA. The partner's session border controller terminates
our dialog, so a `Replaces` tuple we compute refers to a dialog the far side never saw. Oracle and
Ribbon SBCs variously proxy, reject, or silently convert REFER to a fresh INVITE. Separately, we
do not know advisor availability — that state lives in their ACD, so referring to a named advisor
is wrong in principle.

**Mitigation.** Do not design a transfer we control. Target a queue DID or call a REST endpoint on
their dialer and let them re-bridge their own leg — the pattern Indian CCaaS stacks actually
support. Assume REFER-with-Replaces is unavailable until proven otherwise. See ADR-003.
**Trigger.** Week-2 transfer test fails or produces one-way audio.

---

### R-13 · Advisor handoff costs more than it saves
**P** L · **I** 3 · **Score 3** · *Engineering*

Without a working whisper summary and screen-pop, the advisor re-asks everything the bot already
established. The handoff then destroys the time the bot saved.

**Mitigation.** Treat IR-104 and IR-109 as gate items, not enhancements. Measure advisor handle
time post-transfer against the control arm.

---

## 2. Escalated risks — weekly review

| ID | Risk | Score | Owner |
|---|---|---|---|
| R-02 | Code-mixing / spoken amounts | 12 | Engineering |
| **R-14** | **Bot-answered call = abandoned call?** | **10** | **Compliance — resolve before first dial** |
| R-03 | Conversion drop vs control arm | 10 | Engineering + Commercial |
| R-04 | Consent scope larger than assumed | 10 | Compliance |
| R-06 | Partner white-labels a competitor | 10 | Engagement lead |
| R-07 | Fixed-cost base unverified | 9 | Finance |
| R-09 | Timeline outruns scope | 9 | Delivery |
| R-16 | Warm transfer fails at partner SBC | 9 | Engineering |
| R-15 | Unregistered DLT script content | 8 | Compliance |

**R-14 is the one to act on this week.** It is answerable with two emails and it invalidates the
business case if the literal reading holds. Everything else can be managed during the build.

## 3. Risks explicitly accepted

| Risk | Why accepted |
|---|---|
| Slower turn latency than a speech-to-speech competitor | Deliberate. A cascaded pipeline gives us an inspectable transcript, script-adherence proof and the three-year text archive the client requires. Speech-to-speech makes all three a bolt-on. See ADR-001. |
| Not building our own Indic speech models | We will not beat the specialists by training from scratch and should not try. Differentiation is orchestration and analytics. |
| POC operates at a loss | Priced to win a ~₹14 crore annual contract. Payback under one month of production revenue. |
