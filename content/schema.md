# Content Schema

**Status:** synthetic placeholder content. Every line here is `[TransOrg]`-invented and must be
replaced by the BLC-approved script and the SBIC FAQ glossary before any live dialling.

## Why this is data and not code

ADR-002: the LLM never emits customer-facing text. It emits an identifier from a closed set. The
runtime looks up the approved verbatim string for that identifier and plays it. These files *are*
that closed set — they are the runtime artefact, not documentation about it.

Consequence: adding a sentence the bot may say is a content change with a version bump and an
approval reference, never a code change.

## Files

| File | Holds |
|---|---|
| `campaign_vars.yaml` | Declared variable slots. A `{slot}` not declared here is a validation error. |
| `disclosures.yaml` | Mandatory disclosure lines, shared across products. |
| `intents.yaml` | The global intent vocabulary. Node `intent_set`s draw from it. |
| `script/<product>.yaml` | The node graph — one state machine per product. |
| `faq/common.yaml` | FAQ entries valid for every product. |
| `faq/<product>.yaml` | Product-scoped FAQ entries. |
| `out_of_scope.yaml` | Negative examples. `OUT_OF_SCOPE` is a trained class, not a threshold artefact. |
| `handoff.yaml` | What crosses our boundary at transfer, and what comes back. |
| `acceptance.yaml` | Post-transfer acceptance mechanisms. Advisor-side. Stub. |

## Node

```yaml
- id: N04_PITCH                  # unique within the product
  kind: normal                   # normal | terminal | transfer
  requires_disclosure: [D02_FLEXIPAY_TERMS]   # must have played before this node
  intent_set: [INTERESTED, NOT_INTERESTED, HOW_MUCH_EMI]   # node-specific; globals are implicit
  line:
    en: "..."                    # verbatim. {slots} only, never a literal amount.
    hi_latn: "..."
  never_say: ["guaranteed approval"]          # tested against, not merely documented
  routes:                        # NOT `on:` - YAML 1.1 parses that as boolean true
    INTERESTED: N05_INTEREST_PROBE            # target node id, or a FAQ id
    OUT_OF_SCOPE: N19_FALLBACK_TRANSFER       # required on every non-terminal node
```

### Rules the validator enforces

1. Every `routes:` target resolves to a node id in this product or a FAQ id visible to it.
2. Every non-terminal node routes `OUT_OF_SCOPE`, and that route ends at an approved line plus a
   human — never a generated response. There is no syntax for a generative fallback.
3. Every `{slot}` is declared in `campaign_vars.yaml`.
4. Every node is reachable from `entry`, and every path terminates.
5. A node carrying `requires_disclosure` is unreachable unless that disclosure plays first on
   every path to it. This is the mechanical form of "disclosure before restricted topic."
6. Every node has a line in every `required_locale`.
7. FAQ ids are globally unique.
8. Global intents (`intents.yaml` where `global: true`) are routable from every non-terminal node.

## Confidence bands

Routing thresholds are content, not code, because they are tuned per language against real traffic.

```yaml
confidence:
  auto: 0.80        # >= : act on the intent
  flag: 0.50        # >= : act, but tag the turn for async review
                    # <  : deflect to the node's OUT_OF_SCOPE route
```

Per RESEARCH §2.4: one-vs-rest sigmoid, not softmax. Softmax forces probability mass onto some
class by construction and cannot express "none of these" — and a confident misroute on a credit
product is mis-selling.
