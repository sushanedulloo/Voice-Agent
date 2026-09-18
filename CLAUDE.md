# SBI Card Outbound Voice AI — Project Memory

TransOrg Analytics. Engagement at POC stage, September 2026.

## What this is

A multilingual outbound voice agent that takes the **front ninety seconds** of SBI Card's
credit-card cross-sell calls. The bot greets, pitches from a legally approved script, answers
questions from a bank-supplied FAQ glossary, detects interest, and warm-transfers interested
customers to a human advisor who verifies identity, captures consent and books the sale.

Three products in Phase 1: **FlexiPay** (loan on card), **Multicarding** (second card),
**CLIP** (credit limit increase).

We are a **sub-vendor**. The dialer, SIP trunk, advisors and CRM belong to SBI Card's calling
partner. We own only the voice layer and the analytics around it.

## The five constraints that must never be violated

These are not preferences. Each one is a regulatory or contractual obligation, and breaking any
of them is a project-ending event, not a bug.

1. **The script is law.** The BLC-approved script (Business, Legal & Compliance) is a state
   machine. The model selects which approved line to play. It does not author product claims.
   Offer amounts, tenure, interest and fees are read from campaign variables, never generated.
2. **The FAQ glossary is a closed set.** SBI Card supplies a finite database of approved
   question/answer pairs. Off-glossary questions get the node's fallback line and route to a
   human. The model never invents a 61st answer about a credit product.
3. **No PII in our systems.** The calling base arrives stripped of PII and carries a masked
   reference id plus offer variables. Identity verification is the advisor's job, not ours.
   If a design requires us to hold a card number, name or address, the design is wrong.
4. **India-resident inference.** RBI outsourcing expectations and DPDP put model inference,
   storage and the 3-year archive inside India. No foreign API endpoint in the runtime path.
5. **Unbroken audit trail.** Every turn, consent event and disposition is logged and
   correlatable across bot, dialer, CRM and SBI Card systems. Logs are append-only.

## Source of truth

| Document | What it settles |
|---|---|
| `AI BOT Calling .pptx` | **The client's own charter.** Process map, RACI, 7-feature scope, Phase-1 targets, the three product flowcharts. Authoritative on scope. |
| `docs/Context.md` | Engagement brief: economics, competitors, positioning, history. Authoritative on strategy. Note: some cost figures superseded — see below. |
| `cost_model.py` | Bottom-up unit economics. Runnable. Re-run after changing any assumption. |
| `docs/SRS.md` | Numbered, traceable requirements. Every requirement cites its source. |
| `docs/DESIGN.md` | Architecture, diagrams, latency budget, data model. |
| `docs/adr/` | Architecture Decision Records — why, not just what. |

**Where `docs/Context.md` and the charter disagree, the charter wins.** Context.md is our reading of
the engagement; the .pptx is what the client actually wrote.

## Numbers that matter

Run `python cost_model.py` rather than quoting from memory. As of the September 2026 research:

- Direct cost **₹0.22–0.82** per conversation; fully loaded **₹1.67–2.26** at Phase-1 volume.
- `docs/Context.md`'s ₹3.85/min figure is **superseded** — it double-counted the QA team, priced
  runtime TTS for lines that are pre-rendered, and sized infra for 1,000 concurrent sessions.
- Real concurrency requirement: **~121 average, ~243 peak.** Not 1,000.
- Latency: **P50 ≤ 1.0 s, P95 ≤ 1.8 s.** Sub-second P95 over Indian PSTN is not achievable — an
  earlier draft specified it and that was a defect. Vendors claiming sub-500 ms measure inference
  only, excluding network and playout buffers.
- Bot call target: **50 seconds** for pitch-and-probe. Longer if we end up running the CLIP IVR.
- **No published benchmark covers 8 kHz Indic telephony audio.** Every number in circulation is
  16–24 kHz wideband; 5% WER at 16 kHz becomes 12–18% at 8 kHz. Component choices come from our own
  corpus, never a vendor deck. See `docs/adr/ADR-006-measurement-first.md`.

## Open questions that block design decisions

Do not design around a guess on these. Flag and ask.

0. **Is a bot-answered call an "abandoned call" under TCCCPR?** Regulation 2(a) defines one as
   *"an outgoing call in which the sender does not connect the call to a live agent after the call
   is established and is answered by the recipient."* Read literally that is ~88% of our traffic,
   with penalties to ₹10 lakh per violation plus service suspension. **This is existential and it
   is answerable with two emails.** See `docs/RISKS.md` R-14. Nothing dials until it is answered in
   writing.
1. **Who runs the CLIP consent IVR?** The charter's process map and RACI say the BOT Engine is
   Responsible for Consent Capture. All three flowcharts say the advisor runs the IVR. Likely
   reconciliation: bot captures *verbal agreement*, advisor captures the *IVR keypress*. Unconfirmed.
   Decides whether we sit inside the regulated consent chain.
2. **FlexiPay gate: ticket size or record volume?** Flowchart says "Input Volume < 10K",
   scope slide says "Eligible ATS < 10K". Different populations.
3. **Language count: 8 or 9?** Charter lists 8 and omits Gujarati (and duplicates Hindi).
   Shrey's email says 9 including Gujarati.
4. **Does the partner meter media streaming?** We model telephony at ₹0 on their trunk. If they
   charge to fork RTP to us (~₹0.15/min is the Indian norm), that exceeds our entire model cost.
5. **The commercial structure** (MSA with the calling partner, cost-reimbursement billing) is
   asserted in `docs/Context.md` but is **not in the charter deck**. Trace it before relying on it.

## Build order

**FlexiPay first.** Its flow is the only one with no internal contradiction, it targets a segment
nobody calls today (so there is no human baseline to lose against), and targeting precision
matters more than speech quality there — which is where we are strongest. CLIP and Multicarding
follow once the cost-per-booking machinery is proven.

## Conventions

- **Diagrams are Mermaid in Markdown.** No binary image files in the repo — they rot and can't be
  diffed. Mermaid renders on GitHub and in most viewers.
- **Requirements carry IDs** (`FR-`, `NFR-`, `CR-`, `IR-`) and every one cites its source document.
  Anything we invented is marked `[TransOrg]` so the client's asks stay separable from our ideas.
- **ADRs are immutable.** Superseding a decision means a new ADR that references the old one, not
  an edit. Status: Proposed → Accepted → Superseded.
- **Every assumption is a named constant**, never a literal buried in code. `cost_model.py` is the
  pattern: constants at the top, sourced in comments, so client actuals can replace them cleanly.
- Currency in rupees. Volumes in lakh/crore, matching how the client states them.
- Python: stdlib first. This is an analytics and orchestration project, not a framework showcase.

## Working style for this project

- The engagement is judged on a **defensible cost-per-booked-SR number with a human control arm
  standing next to it** — not on a working demo. Instrumentation is a first-class feature, not
  something added at the end.
- Optimise for **time to disqualify**, not time to sell. ~88% of contacts end in a no, and that
  is where all the savings are.
- When something is uncertain, say so and name the question. This deal is decided by a bank's
  InfoSec and compliance review; confident hand-waving fails that review.
