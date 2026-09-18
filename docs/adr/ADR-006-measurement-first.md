# ADR-006 — Build the measurement harness before the agent

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 15 September 2026 |
| **Deciders** | TransOrg engineering |

## Context

We need to choose an ASR engine, a TTS voice and a turn-detection model for eight or nine Indian
languages on 8 kHz telephony audio with heavy code-mixing.

Research across the published literature and vendor documentation produced one unambiguous finding:

> **Essentially no public benchmark data exists for 8 kHz telephony audio.** Every STT and TTS
> latency and accuracy number in circulation is measured at 16–24 kHz wideband.

The gap is not marginal. Independent work indicates a system measuring 5% WER at 16 kHz lands at
**12–18% at 8 kHz**, and Hindi WER on narrowband production traffic routinely exceeds 25–35%.
Peer-reviewed work confirms GSM/2G codecs consistently degrade Indic ASR.

Turn detection is worse. Pipecat's Smart Turn v3 publishes **Marathi 87.6% and Bengali 84.1% — its
weakest tier — and no Hindi figure at all.** LiveKit's detector claims Hindi support with no
published accuracy. Neither addresses 8 kHz.

Meanwhile vendor latency marketing runs **1.5–5× optimistic** against independent measurement, and
a widely-circulated per-stage latency table (STT 60–100 ms / LLM 100–180 ms / TTS 40–80 ms)
reconciles with no measured source and appears to be fabricated.

**We are outside the region where any published number applies.**

## Decision

**Build the measurement harness first. It is Deliverable One of week one, before any dialog logic
exists.**

Specifically, before choosing any component:

1. Obtain **200–500 real call recordings** on the partner's actual carrier, in the actual languages,
   with real code-mixing and real background noise.
2. Run an open, reproducible ASR bake-off on that corpus — reuse the `pipecat-ai/stt-benchmark`
   methodology rather than writing our own.
3. Score on **semantic WER**, not raw WER: weight errors that change meaning — amounts, negations,
   product names — above punctuation and filler. Misreading "nahi" as "haan" matters; a missing
   comma does not.
4. Score **per language, separately**. An aggregate number hides Malayalam and Kannada behind Hindi.
5. Measure turn-detection false-cutoff and false-continue rates on the same corpus, specifically at
   code-switch boundaries.
6. Measure our own end-to-end latency per stage, per utterance.

Component selection is made from those numbers. Not from a vendor deck, and not from ours.

## Rationale

The two things that can kill the economic case — latency on Indic telephony audio, and word error
rate on code-mixed speech — are both cheap to discover in week one and ruinous to discover in week
nine. The existing build roadmap already sequences week 1 this way; this ADR states why, and
raises the harness from a task to a gate.

Code-switching has a specific, non-obvious failure mode worth stating: **speakers pause mid-utterance
to switch languages, and that pause looks exactly like a turn-end** to any endpointing model trained
on monolingual data. A detector tuned on English benchmarks will cut Hindi–English speakers off
mid-sentence. No published benchmark measures this.

## Consequences

**Benefits.** Component choices are defensible with our own numbers — which is also what a bank's
technical evaluation will ask for, and what competitors quoting vendor benchmarks cannot produce.
The harness becomes the regression suite (see `docs/TEST-STRATEGY.md`). It is reusable evidence in
the client conversation.

**Costs.**
- Roughly a week before any conversational code is written. Accept it.
- **Requires real call audio from SBI Card or the partner.** This is a dependency on someone else,
  it needs a data-sharing agreement, and it is on the critical path. Request it at the clarification
  call, not after.
- If real audio cannot be obtained in time, the fallback is degraded: synthetic code-mixed audio
  passed through a G.711 A-law codec round trip. Better than wideband benchmarks, materially worse
  than real carrier audio. Flag any decision made on synthetic data as provisional.

**Standing rule.** No component decision in this project cites a vendor benchmark as its primary
evidence. If we have not measured it on our corpus, we say so.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Pick components from published benchmarks, tune later | The published benchmarks do not measure our conditions. This is not a shortcut, it is a guess with a citation attached. |
| Pick the India-native vendor and move on | Probably the right answer — but "probably right for reasons we cannot show" fails a bank's technical evaluation, and leaves us unable to defend the choice when a competitor produces numbers. |
| Build the agent, measure in the live POC | Puts discovery of a fatal latency or WER problem in month three, after the architecture is committed. |

## References

- `pipecat-ai/stt-benchmark` — open methodology, directly reusable
- arXiv 2606.09335 — codec degradation of Indic ASR; Whisper-based more noise-robust than Conformer
- arXiv 2508.04721 — best available per-stage cascaded latency breakdown (934 ms mean)
- Smart Turn v3/v3.1 model cards — published Indic accuracy, no Hindi figure
- LiveKit LLM latency benchmarks — independent methodology, 4,965 samples/model
