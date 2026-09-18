#!/usr/bin/env python3
"""ADR-005: render every fixed approved span to audio, once, offline.

    python tools/prerender_audio.py
    python tools/prerender_audio.py --pack packs/sbic-blc-2026-10 --voice hf_beta

Run this after any content change. Rendering on demand during a call measured 10-16 seconds a
turn on CPU - the whole point of ADR-005 is that we never pay that at call time.

What it does NOT render: spans carrying a `{slot}`. Those differ per customer, so they are
synthesised live - a second of speech for an amount, not a sentence. That split is why the
measured pre-renderable share is worth knowing, and this prints it.

At 20.4 lakh conversations a month the alternative is paying to re-speak the identical
BLC-approved sentence two million times.
"""

import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent
WAV_CACHE = ROOT / "audio_cache" / "wav"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default=None)
    ap.add_argument("--voice", default="default")
    ap.add_argument("--engine", default="kokoro",
                    help="kokoro (ONNX, en+hi) or parler (torch, all 9)")
    ap.add_argument("--locales", nargs="*", default=None)
    args = ap.parse_args()

    from engine import Content                                   # noqa: PLC0415
    from engine.prerender import (cache_key, enumerate_utterances,   # noqa: PLC0415
                                  get_renderer)

    content = Content(args.pack)
    tts = get_renderer(args.engine)
    WAV_CACHE.mkdir(parents=True, exist_ok=True)

    locales = args.locales or content.locales
    utterances = [u for u in enumerate_utterances(content) if u.locale in locales]

    wanted, skipped_live = {}, 0
    for utt in utterances:
        for span in utt.spans:
            text = span.text.strip()
            if not text:
                continue
            if not span.fixed:
                skipped_live += 1
                continue
            wanted[cache_key(text, utt.locale, args.voice, tts.name, tts.version)] = \
                (text, utt.locale)

    todo = {k: v for k, v in wanted.items() if not (WAV_CACHE / f"{k}.wav").exists()}
    print(f"pack {content.pack_name} @ {content.content_hash}  ·  voice {args.voice}  "
          f"·  {tts.name}")
    print(f"  {len(utterances)} utterances  ·  {len(wanted)} distinct fixed spans  "
          f"·  {skipped_live} live spans skipped")
    print(f"  {len(wanted) - len(todo)} already cached, {len(todo)} to render\n")

    started = time.perf_counter()
    for i, (key, (text, locale)) in enumerate(sorted(todo.items()), 1):
        t0 = time.perf_counter()
        (WAV_CACHE / f"{key}.wav").write_bytes(tts.render_wav(text, locale, args.voice))
        print(f"  [{i:>4}/{len(todo)}] {locale:8} {time.perf_counter() - t0:5.1f}s  "
              f"{text[:58]}")

    # INDEX.json is what makes ADR-005 actually hold: the serving box looks up audio by WHAT IS
    # SPOKEN (text + locale + voice), never by which engine rendered it. Without this the server
    # has to instantiate a TTS engine just to compute a filename - which would mean shipping
    # torch to production to play files that were rendered offline weeks earlier.
    import json as _json
    index_path = WAV_CACHE / "INDEX.json"
    index = {}
    if index_path.exists():
        index = _json.loads(index_path.read_text(encoding="utf-8")).get("spans", {})
    for key, (text, locale) in wanted.items():
        if (WAV_CACHE / f"{key}.wav").exists():
            index[f"{locale}␟{args.voice}␟{text}"] = f"{key}.wav"
    index_path.write_text(_json.dumps(
        {"engine": tts.name, "engine_version": tts.version, "sample_rate": tts.sample_rate,
         "pack": content.pack_name, "content_hash": content.content_hash,
         "spans": index}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  index: {len(index)} spans -> {index_path.relative_to(ROOT)}")

    total = sum(p.stat().st_size for p in WAV_CACHE.glob("*.wav"))
    print(f"\n  rendered {len(todo)} in {time.perf_counter() - started:.0f}s")
    print(f"  cache: {len(list(WAV_CACHE.glob('*.wav')))} files, {total / 1e6:.1f} MB")
    print(f"  -> {WAV_CACHE.relative_to(ROOT)}")
    print("\n  Live spans (campaign variables) are still synthesised per call. That is the")
    print("  design, not a gap - the amount differs for every customer.")


if __name__ == "__main__":
    main()
