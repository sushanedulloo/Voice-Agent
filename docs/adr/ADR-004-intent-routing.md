# ADR-004 — Embedding-first routing cascade, not an LLM call per turn

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 15 September 2026 |
| **Deciders** | TransOrg engineering |
| **Depends on** | ADR-002 |

## Context

ADR-002 fixed the output: the router returns an identifier from a closed set and the runtime plays
the approved line. This ADR decides how that identifier is produced.

The candidate set at any turn is small — the current script node's permitted intents, plus the FAQ
glossary for the product. Glossary size is unknown (open item OI-5); plan for 50–500 entries.

## Decision

**A confidence-banded cascade: embedding retrieval on the hot path, escalating to a constrained
LLM router only on low-confidence turns.**

```
utterance → normalise (numerics, lexicon)
          → embedding retrieval over {node intents ∪ product FAQ entries}
          → confidence band:
              ≥ 0.80  → route, play approved line
              0.50–0.80 → route, play, flag for async review
              < 0.50  → escalate to LLM router (constrained decoding)
                        → still uncertain → OUT_OF_SCOPE → fallback + human
```

## Rationale

**Latency.** Measured: embedding retrieval **16–100 ms**; an LLM router **1–5 s**. Our whole turn
budget is ~1 s at P50 and the routing slot within it is a few hundred milliseconds. An LLM call on
every turn is disqualifying on latency alone, before cost is considered.

**Cost.** Embedding routing is reported ~65× cheaper than LLM classification. At 20 lakh
conversations × ~7 turns, that difference is the entire reasoning line in `cost_model.py`. Our
model currently budgets ₹0.15/conversation for an LLM per turn; this decision makes that a
conservative overestimate, which is where we want the error.

**Accuracy at our scale.** Published guidance: under 15 routes, call the LLM directly; 15–50, use
an embedding router; **50+, use a fine-tuned classifier; 100+, non-negotiable.** A 500-entry
glossary sits firmly in classifier territory. A hybrid cascade is reported within 2% of native LLM
accuracy at roughly half the latency.

**When we do call an LLM, constrain the decoding.** Trie or grammar-based logit masking gives a
*structural* guarantee the output is a valid identifier — not a prompt politely requesting one.
XGrammar adds under 40 µs/token. Asking a model nicely for valid JSON is not a control.

## The part that actually matters: out-of-scope rejection

**A router with no reject option will confidently misroute.** Ask "what's the interest rate on cash
advances?" against a glossary that has a purchase-APR entry and softmax will hand you the purchase
answer with high confidence. *That misroute is mis-selling.* It is the single most likely way this
system causes real customer harm.

Required, not optional:
- **One-vs-rest sigmoid scoring, not softmax.** Softmax forces probability mass onto some class by
  construction — it cannot express "none of these."
- **Calibrated per-class rejection thresholds**, tuned per language. Not one global number.
- **`OUT_OF_SCOPE` trained as an explicit class** on real misrouted traffic, grown continuously
  from production.
- The deflection must itself be an **approved script line** plus a human route. Never a generated
  apology.

## Consequences

**Benefits.** Fits the latency budget. Cheap enough to be irrelevant in the cost model. Confidence
bands give a natural, auditable review queue. Degrades safely — uncertainty routes to a human.

**Costs.**
- Needs labelled examples per glossary entry to bootstrap. We do not have the glossary yet (OI-5).
- Threshold calibration is per-language work, and Indic languages will not share thresholds with
  English.
- A cascade has two accuracy profiles to monitor rather than one.

**Monitoring.** Track routing precision per language and per confidence band. If embedding-router
precision on real traffic falls below ~95%, revisit — a fine-tuned classifier (SetFit/ModernBERT
class) is the next rung, not a bigger LLM.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| LLM router on every turn | 1–5 s latency against a ~1 s total budget. Disqualifying. |
| Fine-tuned classifier only | Better steady-state accuracy at 100+ entries, but needs training data we do not have on day one. **This is the planned successor**, not a rejection. |
| Keyword/regex matching | Collapses on code-mixed speech, which is the majority of our traffic. |
| Put the glossary in the prompt and let the model pick | This is script-in-prompt by another name. See ADR-002 and the τ-bench `pass^k` evidence. |

## References

- Production routing benchmarks: embedding 16–100 ms / 92–96% precision vs LLM router 1–5 s
- XGrammar structured generation, <40 µs/token overhead
- Open-set rejection: one-vs-rest calibration (arXiv 2405.19967); multi-boundary intent learning
