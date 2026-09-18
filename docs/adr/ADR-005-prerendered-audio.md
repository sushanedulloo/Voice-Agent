# ADR-005 — Pre-render approved audio; synthesise only variable spans

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 15 September 2026 |
| **Deciders** | TransOrg engineering |
| **Depends on** | ADR-001, ADR-002 |

## Context

ADR-002 makes the set of emittable utterances finite and known ahead of time. That creates an
option most voice agents do not have: the audio can be produced once, offline, instead of on every
call.

The naive design synthesises every word at call time. On 20.4 lakh conversations a month, that
means paying to re-speak the identical BLC-approved sentence 20.4 lakh times.

## Decision

**Render every fixed approved line to audio once, offline, per language. Cache it. At call time,
play the file. Synthesise at runtime only the spans that vary per customer** — offer amount,
tenure, name.

This is a build step, not a recording studio: the same TTS engine, the same voice, run once per
line rather than once per call.

## Rationale

**Cost.** Full runtime synthesis is ~₹0.88 per conversation. Pre-rendering at an 80% share takes it
to ~₹0.18. Pre-rendering the entire approved inventory is a one-time charge:

| Glossary size | × 9 languages | One-time cost |
|---|---|---|
| 60 lines | 118,800 chars | **₹356** |
| 150 lines | 297,000 chars | ₹891 |
| 500 lines | 990,000 chars | ₹2,970 |

Against roughly ₹18 lakh a month if the same sentences are regenerated per call.

**Latency.** A cache hit removes the TTS stage from the critical path entirely — 80–250 ms saved on
the majority of turns. This partially offsets the latency cost we accepted in ADR-001.

**Compliance, and this is the stronger argument.** A pre-rendered line is *byte-identical on every
call*. There is no per-call synthesis variance to audit, and the audio artefact matches the
registered DLT template exactly (R-15). For the greeting, the identity disclosure and every
regulated phrase, byte-identical output is worth more than the cost saving.

**Numbers are a quality win, not just a cost one.** Spoken amounts in Indian languages are the top
failure mode in BFSI voice. Pre-rendering a number bank — the finite set of offer values that
actually appear in campaigns — is likely *more* accurate than synthesising them live.

## Consequences

**Benefits.** Roughly 18 paise per conversation. TTS off the critical path for most turns.
Byte-identical regulated phrases. A finite, inspectable audio inventory an auditor can enumerate
alongside the text inventory.

**Costs.**
- A build and cache-invalidation step keyed on `script_version` + `glossary_version` + language.
  A stale cache would play a superseded approved line — which is a compliance defect, so the
  version key must be part of the cache key, not an afterthought.
- Storage for the rendered inventory across all languages. Trivially small.
- **Repetition within a call sounds broken.** Across calls it does not matter, since no customer
  hears two. Within a call, a re-prompt repeated identically three times is obviously robotic.
  Mitigate with 2–3 approved variants per re-prompt node.

**Not a dependency.** If pre-rendering were abandoned entirely, loaded cost moves ₹1.67 → ₹1.85 per
conversation. Worth doing, not load-bearing. The business case does not rest on it.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Full runtime TTS | ~₹0.70/conversation more, adds TTS to every turn's critical path, and introduces per-call synthesis variance into regulated audio. |
| Human voice artists for every line | Nine languages × every script node × every glossary entry, re-recorded whenever Compliance changes a word. An ops burden with no quality advantage over a good Indic TTS voice. Reserve for the highest-traffic lines only if listening tests demand it. |
| Cache at runtime (render on first use) | Same steady-state cost, but the first caller in each language hears the latency, and cache state becomes environment-dependent — so staging and production can diverge. Pre-render deterministically instead. |

## Implementation notes

- Cache key: `(script_version, glossary_version, node_id | faq_id, language, variant_index)`.
- Rendering runs in CI on content change, not at deploy time. A BLC content change triggers a
  render job whose output is an immutable, versioned artefact.
- Store the text alongside the audio. The three-year archive (FR-702) needs both, and the text is
  what proves script adherence without anyone listening (NFR-303).
- Variable spans are concatenated, not re-synthesised into the carrier sentence. Splice points need
  prosody attention — this is the one place the approach can sound wrong.
