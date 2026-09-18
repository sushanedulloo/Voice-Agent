#!/usr/bin/env python3
"""ADR-005: render every fixed approved span to audio, once, offline.

    python tools/prerender_audio.py
    python tools/prerender_audio.py --engine parler --locales en hi mr gu bn ta te kn ml
    python tools/prerender_audio.py --engine parler --batch-size 8      # GPU

Run this after any content change. Rendering on demand during a call measured 10-16 seconds a
turn on CPU - the whole point of ADR-005 is that we never pay that at call time.

What it does NOT render: spans carrying a `{slot}`. Those differ per customer, so they are
synthesised live - a second of speech for an amount, not a sentence. That split is why the
measured pre-renderable share is worth knowing, and this prints it.

At 20.4 lakh conversations a month the alternative is paying to re-speak the identical
BLC-approved sentence two million times.

SAFE TO INTERRUPT. The filename is the hash of what is spoken, so a run that dies leaves
complete files and re-running renders only what is missing. There is no resume state to keep.
"""

import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


# How often to rewrite INDEX.json mid-run.
#
# WHY AT ALL: on a borrowed GPU the cache often lives on a mounted drive and the session can be
# reclaimed without warning. Writing the index only at the end would mean an interrupted run
# ships 900 playable clips that the server cannot find. The write is a few hundred kB.
INDEX_EVERY = 100

# Batch size chosen when --batch-size is left at auto, on a CUDA device.
#
# 8 rather than as-large-as-fits: parler pads every row in a batch out to the longest, so a big
# batch spends its extra throughput generating silence it then throws away. 8 measured as the
# knee on an A100-40GB for spans of this length (roughly 40-120 characters).
AUTO_BATCH_CUDA = 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default=None)
    ap.add_argument("--voice", default="default")
    ap.add_argument("--engine", default="kokoro",
                    help="kokoro (ONNX, en+hi) or parler (torch, all 9)")
    ap.add_argument("--locales", nargs="*", default=None)
    ap.add_argument("--cache", default=None,
                    help="where the WAVs go; defaults to audio_cache/wav, or "
                         "$VOICEAGENT_AUDIO_CACHE/wav if set")
    ap.add_argument("--batch-size", type=int, default=0,
                    help=f"0 = auto ({AUTO_BATCH_CUDA} on CUDA, 1 otherwise). Only engines that "
                         f"expose render_wav_batch honour it.")
    ap.add_argument("--device", default=None, help="cuda:0 | cpu (default: cuda if present)")
    ap.add_argument("--dtype", default="auto", help="auto | bfloat16 | float32")
    ap.add_argument("--seed", type=int, default=0,
                    help="parler samples; the seed is what makes a re-render reproduce")
    ap.add_argument("--limit", type=int, default=0,
                    help="render only the first N outstanding spans - use it to time a run "
                         "before committing to the whole thing")
    args = ap.parse_args()

    from engine import Content                                       # noqa: PLC0415
    from engine import prerender as pre                              # noqa: PLC0415

    content = Content(args.pack)
    cache = pathlib.Path(args.cache) / "wav" if args.cache else pre.WAV_CACHE
    cache.mkdir(parents=True, exist_ok=True)

    tts = _build_renderer(pre, args)
    batch_size = _batch_size(tts, args)

    wanted = pre.plan(content, engine=tts.name, version=tts.version,
                      voice=args.voice, locales=args.locales or content.locales)
    todo = pre.outstanding(wanted, cache)

    print(f"pack {content.pack_name} @ {content.content_hash}  ·  voice {args.voice}  "
          f"·  {tts.name}")
    print(f"  {len(wanted)} distinct fixed spans  ·  "
          f"{len(wanted) - len(todo)} already cached, {len(todo)} to render")
    print(f"  -> {cache}")
    print(f"  device {getattr(tts, '_device', 'n/a')}  ·  dtype "
          f"{getattr(tts, '_dtype', 'n/a')}  ·  batch {batch_size}\n", flush=True)

    # Longest first. Two reasons: a batch of similar-length spans wastes the least time
    # generating padding, and the slowest clips land while you are still watching the run rather
    # than in the last five minutes.
    order = sorted(todo.items(), key=lambda kv: (-len(kv[1][1]), kv[0]))
    if args.limit:
        order = order[:args.limit]

    started = time.perf_counter()
    done = 0
    for chunk in _chunks(order, batch_size):
        t0 = time.perf_counter()
        _render_chunk(tts, cache, chunk, args.voice)
        done += len(chunk)
        rate = (time.perf_counter() - started) / done
        locales = "+".join(sorted({loc for _, (loc, _) in chunk}))
        print(f"  [{done:>4}/{len(order)}] {locales:12} "
              f"{time.perf_counter() - t0:5.1f}s  "
              f"eta {(len(order) - done) * rate / 60:5.1f}m  "
              f"{chunk[0][1][1][:48]}", flush=True)
        if done % INDEX_EVERY < batch_size and getattr(tts, "produces_audio", True):
            pre.write_index(cache, wanted, content=content, renderer=tts, voice=args.voice)

    if getattr(tts, "produces_audio", True):
        spans = pre.write_index(cache, wanted, content=content, renderer=tts, voice=args.voice)
        print(f"\n  index: {spans} spans -> {cache / pre.INDEX_NAME}")
    else:
        # A renderer that does not produce audio must not be able to point the server at its
        # output. Without this, a dry run leaves an INDEX.json that makes every approved line
        # play as silence - and a silent compliance disclosure is worse than a failed call.
        print(f"\n  index: NOT written - {tts.name} does not produce audio")

    files = list(cache.glob("*.wav"))
    total = sum(p.stat().st_size for p in files)
    elapsed = time.perf_counter() - started
    print(f"  rendered {done} in {elapsed / 60:.1f}m"
          f"{f' ({elapsed / done:.1f}s each)' if done else ''}")
    print(f"  cache: {len(files)} files, {total / 1e6:.1f} MB")
    missing = len(pre.outstanding(wanted, cache))
    print(f"  {len(wanted) - missing}/{len(wanted)} complete"
          + (f", {missing} still outstanding - re-run to continue" if missing else ""))
    print("\n  Live spans (campaign variables) are still synthesised per call. That is the")
    print("  design, not a gap - the amount differs for every customer.")


def _build_renderer(pre, args):
    """Only parler takes device/dtype/seed; keep the other engines' signatures untouched."""
    cls = pre.RENDERERS.get(args.engine)
    if cls is None:
        raise SystemExit(f"unknown TTS engine {args.engine!r}; have {sorted(pre.RENDERERS)}")
    if cls is pre.ParlerRenderer:
        return cls(device=args.device, dtype=args.dtype, seed=args.seed)
    return cls()


def _batch_size(tts, args) -> int:
    if not hasattr(tts, "render_wav_batch"):
        return 1
    if args.batch_size > 0:
        return args.batch_size
    return AUTO_BATCH_CUDA if str(getattr(tts, "_device", "")).startswith("cuda") else 1


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _render_chunk(tts, cache, chunk, voice):
    """Write each clip as soon as it exists. A clip on disk is progress that survives the run."""
    if len(chunk) == 1 or not hasattr(tts, "render_wav_batch"):
        for key, (locale, text) in chunk:
            (cache / f"{key}.wav").write_bytes(tts.render_wav(text, locale, voice))
        return
    wavs = tts.render_wav_batch([(text, locale) for _, (locale, text) in chunk], voice)
    for (key, _), wav in zip(chunk, wavs):
        (cache / f"{key}.wav").write_bytes(wav)


if __name__ == "__main__":
    main()
