#!/usr/bin/env python3
"""The ADR-006 measurement harness. Deliverable One.

    python tools/benchmark_asr.py --corpus corpus/manifest.csv
    python tools/benchmark_asr.py --corpus corpus/manifest.csv --engines indic_conformer

Manifest is a CSV with columns: path, language, reference
  path       wav file, any sample rate (it is resampled here, deliberately)
  language   one of the pack's locales, or an ISO code the engine knows
  reference  what was actually said, transcribed by a human

WHY THIS EXISTS
---------------
Every published STT accuracy number for Indian languages is measured at 16-24 kHz wideband.
Telephony is 8 kHz - a quarter of the bandwidth - and the same model's word error rate roughly
doubles to triples on it. No public benchmark covers 8 kHz Indic telephony audio. So the number
that decides our component choice does not exist anywhere, and we have to produce it.

The headline output is therefore NOT "which engine is best". It is the DEGRADATION COLUMN:
what each engine loses when the same utterance arrives over a phone line instead of a
microphone. That delta is the number no vendor publishes and the one our design depends on.

Method, stated so it can be attacked:
  - Each clip is evaluated twice: at 16 kHz (the condition vendors quote) and downsampled to
    8 kHz then upsampled back (the condition we actually operate in). Round-tripping rather
    than just downsampling is deliberate - it destroys the high band exactly as a G.711 codec
    does, while keeping the input shape the model expects.
  - WER is computed on lightly normalised text: case folded, punctuation stripped. Numerals are
    NOT normalised, because "sixteen percent" versus "16%" is a real failure for us - the offer
    amount is the one thing the bot must get right.
  - CER is reported alongside because WER is brutal and uninformative for agglutinative
    languages like Malayalam and Kannada, where one wrong morpheme fails a whole word.

Nothing here selects an engine. It produces the table a human reads before deciding.
"""

import argparse
import csv
import json
import pathlib
import re
import statistics
import sys
import time
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent
TELEPHONY_HZ = 8000
WIDEBAND_HZ = 16000

PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
SPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    return SPACE.sub(" ", PUNCT.sub(" ", (text or "").lower())).strip()


def edit_distance(a: list, b: list) -> int:
    """Levenshtein. Stdlib only - no jiwer, no editdistance, it is fifteen lines."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1,          # deletion
                               current[j - 1] + 1,       # insertion
                               previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def wer(reference: str, hypothesis: str) -> float:
    ref = normalise(reference).split()
    if not ref:
        return 0.0
    return edit_distance(ref, normalise(hypothesis).split()) / len(ref)


def cer(reference: str, hypothesis: str) -> float:
    ref = normalise(reference).replace(" ", "")
    if not ref:
        return 0.0
    return edit_distance(list(ref), list(normalise(hypothesis).replace(" ", ""))) / len(ref)


def load_audio(path, target_hz):
    import librosa
    audio, _ = librosa.load(str(path), sr=target_hz, mono=True)
    return audio


def to_telephony(path):
    """16 kHz -> 8 kHz -> 16 kHz. The high band is destroyed the way a G.711 leg destroys it,
    but the model still receives the sample rate it expects, so we measure the audio's loss and
    not a shape mismatch."""
    import librosa
    audio, _ = librosa.load(str(path), sr=TELEPHONY_HZ, mono=True)
    return librosa.resample(audio, orig_sr=TELEPHONY_HZ, target_sr=WIDEBAND_HZ)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--engines", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    from engine.asr_engines import available, load_engine       # noqa: PLC0415

    manifest = pathlib.Path(args.corpus)
    if not manifest.exists():
        raise SystemExit(
            f"no corpus at {manifest}.\n"
            "This harness needs 200-500 real call recordings from the partner's actual carrier,\n"
            "in the actual languages, with real code-mixing and real background noise\n"
            "(DELIVERY-PLAN 0.3). Synthetic or studio audio produces a number that flatters us\n"
            "and predicts nothing.")

    with open(manifest, newline="", encoding="utf-8") as fh:
        clips = list(csv.DictReader(fh))
    if args.limit:
        clips = clips[:args.limit]

    names = args.engines or available()
    print(f"corpus {manifest}  ·  {len(clips)} clips  ·  engines: {', '.join(names)}\n")

    results = []
    for name in names:
        try:
            engine = load_engine(name)
        except Exception as exc:                                  # noqa: BLE001
            print(f"  {name}: unavailable ({type(exc).__name__}: {exc})")
            continue

        for condition, loader in (("16khz", lambda p: load_audio(p, WIDEBAND_HZ)),
                                  ("8khz", to_telephony)):
            for clip in clips:
                path = (manifest.parent / clip["path"]).resolve()
                lang = clip["language"]
                if lang not in engine.languages:
                    continue
                audio = loader(path)
                t0 = time.perf_counter()
                hyp = engine.transcribe(audio, lang)
                elapsed = time.perf_counter() - t0
                results.append({
                    "engine": name, "condition": condition, "language": lang,
                    "wer": wer(clip["reference"], hyp),
                    "cer": cer(clip["reference"], hyp),
                    "rtf": elapsed / max(len(audio) / WIDEBAND_HZ, 1e-6),
                    "reference": clip["reference"], "hypothesis": hyp,
                    "path": clip["path"],
                })

    if not results:
        raise SystemExit("no results - no engine handled any clip in this corpus")

    # ---- the table ---------------------------------------------------------
    by = defaultdict(list)
    for r in results:
        by[(r["engine"], r["language"], r["condition"])].append(r)

    print(f"{'engine':26} {'lang':5} {'WER 16k':>8} {'WER 8k':>8} {'degrade':>9} "
          f"{'CER 8k':>8} {'RTF 8k':>7}  n")
    print("-" * 82)
    for (eng, lang), _ in sorted({(e, l): 1 for e, l, _ in by}.items()):
        wide = by.get((eng, lang, "16khz"), [])
        tel = by.get((eng, lang, "8khz"), [])
        if not wide or not tel:
            continue
        w16 = statistics.mean(r["wer"] for r in wide)
        w8 = statistics.mean(r["wer"] for r in tel)
        c8 = statistics.mean(r["cer"] for r in tel)
        rtf = statistics.median(r["rtf"] for r in tel)
        degrade = (w8 - w16) / w16 if w16 else float("inf")
        print(f"{eng:26} {lang:5} {w16:7.1%} {w8:8.1%} {degrade:+8.0%} "
              f"{c8:8.1%} {rtf:7.2f}  {len(tel)}")

    print("\n  RTF = real-time factor at 8 kHz; < 1.0 means faster than real time, which is the")
    print("  minimum bar for a streaming leg before any batching or GPU.")
    print("  The degrade column is the finding. No vendor publishes it.")

    out = pathlib.Path(args.out or ROOT / "runs" / "asr_benchmark.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  per-clip results -> {out.relative_to(ROOT)}")
    print("  Every hypothesis is kept, so a bad number can be traced to the clip that caused it.")


if __name__ == "__main__":
    main()
