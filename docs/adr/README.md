# Architecture Decision Records

An ADR captures **why**, not just what. The code shows what we did; these explain what we chose
against and what we accepted in exchange.

## Rules

- **ADRs are immutable.** Superseding a decision means writing a new ADR that references the old
  one, then marking the old one `Superseded by ADR-NNN`. Never edit a decision after it is Accepted.
- Status: `Proposed` → `Accepted` → `Superseded` (or `Rejected`, kept for the record).
- One decision per record. If it needs two headings, it is two ADRs.
- Every ADR names the alternatives and why they lost. An ADR with no rejected alternative is not a
  decision, it is a description.

## Index

| # | Decision | Status | Consequence in one line |
|---|---|---|---|
| [001](ADR-001-cascaded-pipeline.md) | Cascaded speech pipeline, not speech-to-speech | Accepted | We lose the latency comparison deliberately, and gain an auditable transcript |
| [002](ADR-002-response-selection.md) | Response selection, not generation | Accepted | Hallucination on product claims is structurally zero, not merely rare |
| [003](ADR-003-telephony-topology.md) | The partner owns the call; we are a media endpoint | Accepted | No SBC compatibility matrix, and the regulatory perimeter stays theirs |
| [004](ADR-004-intent-routing.md) | Embedding-first routing cascade | Accepted | Fits the latency budget; out-of-scope rejection is the safety-critical part |
| [005](ADR-005-prerendered-audio.md) | Pre-render approved audio, synthesise only variables | Accepted | ₹0.18/conversation, TTS off the critical path, byte-identical regulated phrases |
| [006](ADR-006-measurement-first.md) | Build the measurement harness before the agent | Accepted | No published benchmark covers our conditions, so we make our own numbers |

## Decisions still open

These are not ADRs yet because they are blocked on information we do not have. Each is tracked as
an open item in [`../SRS.md` §10](../SRS.md#10-open-items).

| Pending decision | Blocked by |
|---|---|
| Consent module: verbal agreement only, or bot-run IVR | OI-1 — the charter contradicts itself |
| ASR and turn-detection engine selection | ADR-006 measurement + real call audio from the client |
| Self-hosted from day one, or managed APIs first | InfoSec review (R-05) |
| Router bootstrap approach | OI-5 — glossary not yet seen |
| Transfer mechanism | Partner interface control document |

## Template

```markdown
# ADR-NNN — <decision in one line>

| | |
|---|---|
| **Status** | Proposed |
| **Date** | |
| **Deciders** | |
| **Depends on** | |

## Context
What forces are at play? What constraint makes this a decision rather than a default?

## Decision
What we are doing. Stated in the active voice.

## Rationale
Why. Evidence where evidence exists; judgement named as judgement where it does not.

## Consequences
Benefits and costs. Costs are not optional — an ADR with no downside is marketing.

## Alternatives considered
| Alternative | Why rejected |

## References
```
