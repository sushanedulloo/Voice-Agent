# Project Documentation

AI-BOT Outbound Telesales Voice Agent · TransOrg Analytics · September 2026

## Where to start

| If you are… | Read |
|---|---|
| New to the engagement | [`Context.md`](Context.md) — the business, the competition, the economics |
| Running it | [`RUNBOOK.md`](RUNBOOK.md) — every command, from a cold machine |
| Picking up where we left off | [`APPROACH.md`](APPROACH.md) — next steps and the GPU render handoff |
| Picking up the build | [`../CLAUDE.md`](../CLAUDE.md), then [`SRS.md`](SRS.md), then [`DESIGN.md`](DESIGN.md) |
| Reviewing the architecture | [`DIAGRAMS.md`](DIAGRAMS.md) and [`adr/`](adr/README.md) |
| From the client's InfoSec | [`SRS.md` §6](SRS.md#6-compliance-requirements) and [`RISKS.md`](RISKS.md) |
| Running the numbers | [`../cost_model.py`](../cost_model.py) — runnable, not a spreadsheet screenshot |
| Deciding what to worry about | [`RISKS.md`](RISKS.md) |

## The document set

| Document | Purpose | Status |
|---|---|---|
| [`SRS.md`](SRS.md) | Numbered, traceable requirements. Every one cites its source. | Draft |
| [`DESIGN.md`](DESIGN.md) | Architecture, latency budget, scaling, failure handling | Draft |
| [`DIAGRAMS.md`](DIAGRAMS.md) | C4 views, sequence diagrams, state machine, ER model, deployment | Draft |
| [`adr/`](adr/README.md) | Architecture Decision Records — six accepted | Active |
| [`TEST-STRATEGY.md`](TEST-STRATEGY.md) | Test levels, compliance evidence, evaluation method | Draft |
| [`RISKS.md`](RISKS.md) | Risk register, scored, with triggers and owners | Active |
| [`api/`](api/) | Interface contracts — `openapi.yaml` | Draft |
| [`RUNBOOK.md`](RUNBOOK.md) | Every command, from a cold machine | Active |
| [`APPROACH.md`](APPROACH.md) | Where we are, what is next, the GPU handoff | Active |
| [`Context.md`](Context.md) | Engagement brief. Superseded on cost — see point 3 | Reference |
| [`DELIVERY-PLAN.md`](DELIVERY-PLAN.md) | Sequenced plan to the Day-30 gate | Active |
| [`RESEARCH.md`](RESEARCH.md) | What the field actually does, with sources | Reference |
| [`SCRIPT.md`](SCRIPT.md) | The synthetic script, annotated | Draft |

## Reading the requirement IDs

| Prefix | Meaning |
|---|---|
| `FR-` | Functional requirement |
| `NFR-` | Non-functional — performance, scale, observability, maintainability |
| `CR-` | Compliance requirement. Failure here is a breach, not a defect |
| `IR-` | External interface requirement |
| `DR-` | Data requirement |
| `OI-` | Open item — blocked on client input |
| `R-` | Risk |
| `ASM-` / `CON-` | Assumption / constraint |

Sources are cited as `CH-Sn` (charter slide n), `CH-RACI`, `EM-1`/`EM-2` (Shrey's emails), `CTX`
(engagement brief), or `[TransOrg]` for anything we originated. **`[TransOrg]` items are negotiable;
charter-sourced items are the contract.**

## The four things worth knowing before you read anything else

1. **We are a sub-vendor.** The dialer, trunk, CRM and advisors belong to the calling partner. We
   own the voice layer and the analytics around it, and nothing else.
2. **The model chooses; it does not speak.** Every utterance resolves to BLC-approved content. This
   is a regulatory requirement, not a design preference — and it is what makes compliance provable
   rather than merely measured.
3. **Our own cost is ₹1.67–2.26 per conversation**, not the ₹3.96 the engagement brief states. The
   earlier figure double-counted the QA team and oversized the infrastructure fourfold.
4. **[R-14](RISKS.md) is unresolved and it is existential.** Under TCCCPR, a bot-answered call never
   connected to a live agent may literally be an "abandoned call". That describes ~88% of our
   traffic. Two emails resolve it; discovering it in month three does not.

## Conventions

- Diagrams are Mermaid in Markdown. No binary images — they rot and cannot be diffed.
- ADRs are immutable. Superseding means a new record, not an edit.
- Every assumption is a named, sourced constant. `cost_model.py` is the pattern.
- Where `Context.md` and the charter deck disagree, **the charter wins.**
- All documentation lives here. The repository root carries only `README.md` and build files.
