# Runbook

Every command, from a cold machine. Windows paths; `cmd` or PowerShell both work.

---

## 0. One-time setup

```bat
cd C:\Users\TransOrg\Documents\Outbound
python -m pip install -r requirements.txt
```

Nine runtime dependencies. **No PyTorch** — the serving side plays pre-rendered audio and never
loads a speech model (ADR-005). Build-time deps are separate, see §6.

Speech models (~8 GB, one-time). The AI4Bharat repos are gated, so accept the terms on each
model page first, then:

```bat
hf auth login
python tools\fetch_models.py
```

---

## 1. Check the build is sound

Run these three before anything else. They take seconds and they are the difference between
"it started" and "it works".

```bat
python tools\validate_content.py
python tests\test_engine.py
python tools\probe_router.py
```

Expect `0 error(s)`, `17 passed`, and a leak/over-deflect pair. **A non-zero validator is a
hard stop** — it means the content pack can express a call that dead-airs or an offer reachable
without its disclosure.

---

## 2. Start the call console  ← the product

```bat
python apps\server.py
```

Open **http://localhost:8077** in Chrome or Edge.

1. **Customer** dropdown — picks a real record: name, product, language, offer variables
2. **Start call**, allow the microphone
3. Talk. On `hi`/`ta`/`te`/`kn`/`ml`/`mr`/`gu`/`bn` the recogniser is ours (indic-conformer,
   on this machine). On `en` it falls back to the browser — English is not in that model.

Worth trying:

| Say | Expected |
|---|---|
| "yes speaking" / "जी हाँ" | advances past identity |
| "what is the interest rate" | answers from the glossary with *this customer's* rate |
| "what's the rate on a cash withdrawal" | **refuses** and fetches a human — the mis-sell guard |
| "stop calling me" / "बार बार मत करो" | DNC close, mood flips to `irritated` |
| talk over the bot | barge-in, truncation logged |
| "connect me" | hold music → **dialpad** → press 1 to accept, 2 to decline |

Right-hand panel, live: node · disclosures played · path · **sentiment trajectory** ·
**compliance rules** · handoff payload.

**8 kHz telephony** toggle in the header band-limits the audio exactly as a phone line does.

---

## 3. Run a campaign and read the numbers

```bat
python tools\make_base.py --rows 2000
python apps\campaign.py  --base runs\base.csv --concurrency 243 --run-id r3
python tools\report.py   --run r3
python tools\insights.py --run r3 --html runs\r3\dashboard.html
```

Open `runs\r3\dashboard.html`. That is charter features 2, 3, 4 and 6 on one page.

`--run-id` must be new each time. Reusing one is refused — appending would merge two campaigns
into one audit file and every metric downstream would be computed across both.

---

## 4. The API (how SBIC's partner would integrate)

```bat
set OUTBOUND_API_TOKEN=devtoken
python apps\api.py
```

http://localhost:8078/docs for Swagger.

```bat
curl -s localhost:8078/ready
curl -s localhost:8078/reports/daily  -H "Authorization: Bearer devtoken"
curl -s localhost:8078/reports/funnel -H "Authorization: Bearer devtoken"
curl -s localhost:8078/calls/<call-id>/evidence -H "Authorization: Bearer devtoken"
```

The evidence packet is the compliance artefact: which content hash spoke, which disclosures
played in what order, and whether anything unapproved was ever uttered.

---

## 5. Swapping in SBIC's script

Content is a directory, not a deployment. When the BLC script arrives:

```bat
python tools\import_script.py --in incoming\client-script --out packs\client-blc-2026-10 ^
                              --name client-blc --approval-ref BLC-2026-1012
python tools\validate_content.py --pack packs\client-blc-2026-10
python apps\server.py            --pack packs\client-blc-2026-10
```

The pack will not load until the validator passes. That is deliberate.

---

## 6. Rendering the voices (build-time)

`indic-parler-tts`, all nine languages, 1,089 clips. **Do this on a GPU.**

### 6a. Colab A100 — the normal route

[**Open the notebook**](https://colab.research.google.com/github/sushanedulloo/Voice-Agent/blob/main/notebooks/render_audio_colab.ipynb)
· source: [`notebooks/render_audio_colab.ipynb`](../notebooks/render_audio_colab.ipynb)

Under an hour, against 15–50 on the laptop. The notebook is a thin driver; the logic is in
[`tools/colab_env.py`](../tools/colab_env.py), so it is reviewable, importable and diffable like
any other file in the repo.

Needs, once: an **A100** runtime and a Colab secret `HF_TOKEN` for the gated model. The render
mirror at [`sushanedulloo/Voice-Agent`](https://github.com/sushanedulloo/Voice-Agent) is public,
so the clone needs no GitHub token. No token is ever written into the notebook.

Output goes straight to `MyDrive/VoiceAgent-audio/wav/` as each clip is produced, so a reclaimed
session loses nothing — re-run the render cell and it continues. Bring it home by unzipping into
`audio_cache/wav/`.

### 6b. Any other GPU box

```bash
pip install -r requirements-build.txt     # torch 2.5.1 + torchaudio 2.5.1, pinned TOGETHER
python tools/tts_check.py                 # 9 samples, ~2 min — LISTEN first
python tools/prerender_audio.py --engine parler --batch-size 8
python tools/render_status.py  --engine parler --verify
```

A mismatched torch/torchaudio pair breaks torchaudio's native extension and `parler_tts` will
not import at all. `--batch-size` is the whole GPU story: one clip at a time leaves the card
idle, because the batch dimension is 1.

### 6c. CPU fallback (WSL)

~120 s per clip — about 36 hours, so this is a last resort.

```bash
wsl -d Ubuntu && cd /mnt/c/Users/TransOrg/Documents/Outbound
source .venv-tts/bin/activate
python tools/prerender_audio.py --engine parler --locales en hi mr gu    # worker A
python tools/prerender_audio.py --engine parler --locales bn ta te kn ml # worker B
```

Two workers, not three — parler holds ~4 GB each and WSL has 12 GB (`~/.wslconfig`).

Torch belongs **only** to this step. It will not load on Windows (Smart App Control), and it
does not need to: the serving box plays files.

### Then, wherever it ran

Restart `apps/server.py`. Audio resolves through `audio_cache/wav/INDEX.json` by *what is
spoken*, not by which engine spoke it, so the swap needs no code change. Confirm with
`/api/config` → `prerendered_engine` should read `indic-parler-tts`.

Every render step is safe to interrupt and safe to re-run: a clip's filename **is** the SHA-256
of what it says, so partial results are complete files and `tools/render_status.py` says what is
left. Point any of these tools at a different cache with `--cache`, or set
`$VOICEAGENT_AUDIO_CACHE` once and they all follow it.

---

## 7. Ports

| Port | What | Start |
|---|---|---|
| 8077 | Call console | `python apps\server.py` |
| 8078 | Production API | `python apps\api.py` |

Both bind `127.0.0.1` only.

To free a stuck port:

```powershell
Get-NetTCPConnection -LocalPort 8077 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

---

## 8. What is real and what is not

Read this before showing anyone.

**Real:** dialogue policy, disclosure enforcement (static proof *and* runtime guard), out-of-scope
refusal, barge-in, append-only audit, sentiment in 9 languages, IVR, cost reporting, the API,
and ASR on 8 Indian languages.

**Not real, and labelled in the UI:**

- Content is **synthetic** — `[TransOrg]`-invented, not BLC-approved
- The **advisor leg is simulated**, so the funnel's human arm is *modelled*, not measured
- The **mel front-end is unvalidated** against the reference implementation
- The **router is a TF-IDF stand-in** — it cannot represent negation without hand-enumerated
  examples, and it leaks ~17% on held-out off-glossary questions
- **Sentiment is uncalibrated** against human labels
- There is **no telephony**

**And the one that outranks all of it:** nothing dials until **R-14** is answered in writing —
whether a bot-answered call is an "abandoned call" under TCCCPR 2(a). Penalties reach ₹10 lakh
per violation. It is answerable with two emails and it has been the top of the list since day one.
