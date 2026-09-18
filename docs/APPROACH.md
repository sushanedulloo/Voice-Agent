# Approach and next steps

Branch `VoiceAgent`. Written 18 Sep 2026.

Read [`../README.md`](../README.md) for what the system is and [`RUNBOOK.md`](RUNBOOK.md) for how to run it. This file is the
plan: where we are, who does what next, and what we are deliberately not doing yet.

---

## Where we are

A working multilingual outbound voice agent. Nine languages, three products, closed-set
dialogue with enforced disclosures, IVR handoff, sentiment, analytics, an audit trail and a
production API.

```
content     9 locales · 74 nodes · 54 FAQ · 13 out-of-scope categories · 0 validator errors
tests       17/17
ASR         ai4bharat/indic-conformer-600m on onnxruntime, 8 Indian languages, no PyTorch
TTS         ai4bharat/indic-parler-tts, rendering (see below)
console     apps/server.py   :8077   browser, real mic, dialpad
API         apps/api.py      :8078   10 endpoints per docs/api/openapi.yaml
```

All seven charter capabilities exist. Six of them are analytics, which is why every turn has
been written to an append-only log since the first working call — the reporting reads that log
rather than needing new plumbing.

---

## Immediate: finish the voice render  → **Colab A100**

The only outstanding build task. ~1,089 audio clips across nine languages.

On this laptop it runs at roughly 50–170 s per clip, so 15–50 hours depending on contention.
On an A100 with batching it is **under an hour**. That is the whole reason it moved.

### [→ Open the render notebook](https://colab.research.google.com/github/sushanedulloo/Voice-Agent/blob/main/notebooks/render_audio_colab.ipynb)

Source: [`notebooks/render_audio_colab.ipynb`](../notebooks/render_audio_colab.ipynb). Pick an
**A100** runtime, add two Colab secrets (`GH_TOKEN`, `HF_TOKEN`), run the cells.

The notebook is nine lines of driver. Everything it does lives in
[`tools/colab_env.py`](../tools/colab_env.py), because a notebook is not a reviewable artefact —
cells cannot be imported, linted or diffed sensibly, and the version that ran is whatever
happened to be in the browser. If Colab disappears tomorrow the render still runs from a
terminal.

Clips are written to `MyDrive/VoiceAgent-audio/wav/` as they are produced, not copied at the
end. A Colab session can be reclaimed without warning; a run that dies at clip 700 has banked
700 clips and the next run does the remaining 389.

### On any other GPU box

```bash
git clone <repo> && cd VoiceAgent && git checkout colab-gpu-render

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-build.txt      # torch 2.5.1 + torchaudio 2.5.1, PINNED TOGETHER

# accept the licences on both ai4bharat model pages first (they are gated), then:
hf auth login
python tools/fetch_models.py               # ~8 GB

python tools/tts_check.py                  # 9 samples, ~2 min — LISTEN before the long run
python tools/render_status.py --engine parler          # what is outstanding

python tools/prerender_audio.py --engine parler --batch-size 8

python tools/render_status.py --engine parler --verify # expect 1089/1089 and 0 broken
```

Then ship back `audio_cache/wav/` — about 140 MB. Any transport is fine.

### Why this merges with no coordination

A clip's filename **is** the hash of what it says:

```
filename = sha256(text + locale + voice + engine + engine_version)
```

The cache is content-addressed. Files from another machine merge by copying into
`audio_cache/wav/`. There is no resume protocol because none is needed — if two machines render
the same span they produce the same filename with identical content. Partial results are useful
on their own; whatever arrives is progress.

`tools/prerender_audio.py` skips anything already on disk, so re-running it is always safe and
`tools/render_status.py` says what is left.

### Receiving the cache

```bash
cp -r incoming_wav/* audio_cache/wav/
python tools/render_status.py --verify
python apps/server.py
```

Confirm at `/api/config` → `prerendered_engine` should read `indic-parler-tts`, not
`kokoro-82m-onnx`. Nothing else changes: audio resolves by **what is spoken**, never by which
engine spoke it, so swapping engines needs no code change.

### One judgement call for a human

Listen to a **full call**, not single lines. The samples were one sentence each; a real call
plays short spans back to back — `"Am I speaking with"` + `"Tushar"`. That join is where
concatenated TTS usually shows a seam. If it is audible the fix is rendering common two-span
combinations whole — known technique, costs render time, not redesign. Better to find it on
synthetic content than on SBIC's.

---

## Next: when SBIC's BLC script arrives

Four commands. No code changes — that is what the content-pack design is for.

```bash
python tools/import_script.py --in incoming/client-script --out packs/client-blc \
                              --name client-blc --approval-ref BLC-2026-xxxx
python tools/validate_content.py --pack packs/client-blc      # 0 errors or it does not run
python tools/prerender_audio.py  --pack packs/client-blc --engine parler --locales en hi mr gu bn ta te kn ml
python apps/server.py            --pack packs/client-blc
```

The synthetic audio becomes orphaned — different words, different hashes. Delete it.

**After that first render, changes are cheap.** Because the cache is keyed by text, BLC revising
eight lines in month four re-renders eight clips, not the corpus. We never become the reason
legal moves slowly.

**Raise early, and nobody has yet:** BLC approves what the bot *says*. Who approves what it
*sounds like* — voice, gender, pace, per language? Send a short sample pack with the script
questions. Cheap now; expensive after 5,000 clips are rendered in the wrong voice.

---

## Engineering backlog, in the order it matters

1. **Replace the router.** It is a TF-IDF stand-in: ~17% of held-out off-glossary questions
   leak to an in-scope answer, and it cannot represent negation without hand-enumerated
   examples — `"इंटरेस्ट नहीं है"` scored as INTERESTED until the negated forms were added by
   hand, in all nine languages. Embeddings capture that natively. ADR-004 specifies the design.
   **This is the single highest-value engineering task** and it is what stands between 79%
   containment on personas and a number we would defend to a client.

2. **Validate the mel front-end.** `engine/asr_engines.py` reimplements it from NeMo's
   documented parameters because the shipped one is TorchScript and torch will not load on the
   dev machine. Feature extraction that is subtly wrong does not crash — it quietly costs
   accuracy and the model gets blamed. Compare against `assets/preprocessor.ts` on a box where
   torch runs. Every engine reports `validated = False` until then.

3. **Wire Whisper for English.** indic-conformer covers 22 *Indian* languages; English is not
   among them. Two-model ASR split, not one.

4. **Run the 8 kHz benchmark.** `tools/benchmark_asr.py` exists and has never run because there
   is no corpus. Its headline output is the degradation column — what each engine loses over a
   phone line — which no vendor publishes.

5. **Number components for TTS.** `indicative_emi` has ~817 distinct values per 2,000 records,
   so amounts are effectively unique per customer — ~78 audio-hours of live synthesis monthly at
   Phase-1 volume. Pre-rendering 0–99 plus सौ/हज़ार/लाख makes every amount a concatenation and
   takes runtime TTS to zero.

6. **Calibrate sentiment.** Lexicon-based, uncalibrated, and the booking-rate-by-sentiment
   ordering currently comes out counterintuitive — which is evidence it needs human labels, not
   a finding about customers.

7. **CRM write-back.** `content/handoff.yaml`'s `inbound` block is unimplemented, so the
   advisor leg is simulated and the funnel's human arm is *modelled*, not measured. Without it
   we can count transfers but not outcomes, and cost-per-booked-SR stays an estimate.

8. **Telephony.** No SIP, no media endpoint. R-16 (warm transfer failing at the partner's SBC)
   is the second-highest engineering risk and is untested. Blocked on the ICD and a test trunk.

---

## Blocked on the client — and these outrank everything above

1. **R-14. The abandoned-call ruling.** Under TCCCPR 2(a) an abandoned call is one where the
   sender does not connect to a live agent. Read literally that is ~88% of our traffic — every
   call the bot disqualifies. Penalties reach ₹10 lakh per violation plus service suspension.
   **Nothing dials until this is answered in writing**, by the partner's compliance team *and*
   their access provider. It is answerable with two emails and it has been top of this list
   since day one.

2. **FlexiPay step 10a.** *"Customer is verified using their billing address PIN code and year
   of birth"* — the flowchart names no actor. The identical step in the Multicarding flow is
   explicitly the Ops advisor. If SBIC expects the **bot** to do it, our no-PII constraint and
   their flowchart cannot both hold, and we need to know now rather than in month three.

3. **The BLC script and FAQ glossary** (OI-5). The pack is built to receive them.

4. **200–500 real call recordings** on the partner's actual carrier. Every component choice is
   provisional without them — no published benchmark covers 8 kHz Indic telephony.

5. **ICD and a test SIP trunk.**

---

## What is real and what is not

Say this out loud before any demo.

**Real:** dialogue policy, disclosure enforcement (static proof *and* runtime guard),
out-of-scope refusal, barge-in, append-only audit, sentiment across nine languages, the IVR,
cost reporting, the API, and ASR on eight Indian languages.

**Not real, and labelled in the UI:**

- Content is **synthetic**, `[TransOrg]`-invented, not BLC-approved
- The **advisor leg is simulated** — the funnel's human arm is modelled, and the endpoint says so
- The **mel front-end is unvalidated**
- The **router is a stand-in**
- **Sentiment is uncalibrated**
- There is **no telephony**

It is ready to demo and ready to be attacked by a technical reviewer. It is not ready to dial —
and that is the regulation, not the code.
