# ADR-002 — Response selection, not response generation

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 15 September 2026 |
| **Deciders** | TransOrg engineering |
| **Depends on** | ADR-001 |

## Context

The bot speaks to cardholders about credit products. SBI Card supplies two content assets: a
BLC-approved script, and a FAQ glossary database of approved question/answer pairs (`CH-S3`
steps 3 and 4).

If the model generates its own phrasing about interest rates, fees or terms, three things break at
once:

- **Mis-selling exposure.** The customer did not understand what they agreed to. Complaints,
  refunds, regulatory attention. SBI Card is liable, not us.
- **Unregistered DLT script.** TCCCPR requires commercial voice scripts to be registered as
  templates by the Principal Entity. Generated phrasing is unregistered content on every call (R-15).
- **Unprovable compliance.** "Did the bot say something unapproved?" becomes a statistical question
  answered by sampling, rather than a structural property.

Published measurement makes the third point concrete. τ-bench (arXiv 2406.12045) introduced
`pass^k` — the probability that *all* k trials succeed — and measured frontier function-calling
agents below 25% `pass^8` on retail tasks, with **policy adherence degrading as conversation
length grows**. Insurance-domain work (INSURE-Dial, arXiv 2602.18448) reproduces the same decay
and adds that compliance degrades further when obligations shift between conversation phases —
which is exactly the shape of a sales script.

An LLM asked to *follow* a script will drift. Not often, but measurably, and a bank audits the
tail.

## Decision

**The LLM never emits customer-facing text.** It emits a label from a closed set — a script node
id, a FAQ entry id, or `OUT_OF_SCOPE`. The runtime looks up the approved verbatim string for that
label and plays it.

```
ASR → state machine (owns the script, restricts candidates)
    → router (returns an ID from the approved set ∪ {OUT_OF_SCOPE})
    → lookup: ID → approved verbatim utterance
    → TTS / cached audio
```

Three rules make this hold:

1. **Every framework in this space ships a generative escape hatch. Disable all of them.** Rasa's
   rephraser, NeMo Guardrails' `llm continuation` fallback, Pipecat's free-text nodes. `OUT_OF_SCOPE`
   routes to an approved deflection line and a human, and to nothing else.
2. **The script lives in the state machine, never in a prompt.** Prompt-embedded business logic is
   the documented failure mode — the *Conversation Routines* paper (arXiv 2501.11613) concedes in
   its own limitations that guardrails "mitigate but complete elimination remains challenging",
   and its future work is to compile the spec down to a state machine.
3. **Phase is tracked explicitly**, not inferred by the model, because that is where compliance
   decays first.

## Consequences

**Benefits.**
- Hallucination rate on product claims is structurally zero, not merely low. There is a finite,
  pre-approved utterance inventory an auditor can enumerate.
- FR-203 is verifiable by inspection: the set of emittable strings is a database table.
- Makes ADR-005 (pre-rendered audio) possible, because the utterance set is finite and known ahead
  of time.
- Satisfies the DLT template-registration constraint as a side effect.

**Costs.**
- The bot cannot handle a question outside the glossary. This is intended — but it means glossary
  quality directly caps conversation quality, and we do not control the glossary.
- Conversation can feel rigid if the approved set is thin. Mitigate with multiple approved variants
  per node, particularly for re-prompts (ADR-005).
- **Whether this survives contact with reality depends on open item OI-5.** We have not seen the
  glossary. If SBI Card expects open-ended Q&A about a credit product, this ADR needs revisiting —
  and so does their compliance position.

**Non-consequence.** This does not make the bot less conversational. Understanding the customer is
still a genuine, difficult, live language problem. Only the output path is constrained.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Generate freely, validate output with a guardrail framework | Inline guardrails cost 100–300 ms against a ~50–100 ms budget slot; one independent study measured NeMo Guardrails at >1.4 s mean, >4 s P95. And validation is probabilistic where selection is structural. |
| Generate, then check with an NLI entailment gate | Same latency objection inline. Valuable **asynchronously** over transcripts as compliance evidence — adopted for that purpose, not as a control. |
| Constrained decoding to force approved output | Guarantees well-formed output, not *approved* output. Useful for the routing label (adopted, see ADR-004), not a substitute for selection. |
| Fine-tune a model on approved content | Reduces drift, does not eliminate it, and cannot be proven to an auditor. |

## Compliance evidence

Async over every call transcript (not sampled), producing an evidence packet per call: call id,
transcript span with timestamp, audio pointer, **script version + glossary version + evaluator
version**, rule id, rationale. Every confirmed miss becomes a replayable regression test.

Targets adopted from published script-adherence methodology: required-line delivery ≥99%,
prohibited-response confirmed misses = 0, identity-before-disclosure = 100%.

## References

- τ-bench, arXiv 2406.12045 — `pass^k`, policy adherence decay with dialogue length
- INSURE-Dial, arXiv 2602.18448 — phase-aware compliance degradation in regulated dialogue
- FlowAgent, arXiv 2502.14345 — out-of-workflow query handling
- Conversation Routines, arXiv 2501.11613 — documented failure of prompt-embedded business logic
- Rasa CALM — LLM for dialogue *understanding*, deterministic engine for dialogue *policy*
