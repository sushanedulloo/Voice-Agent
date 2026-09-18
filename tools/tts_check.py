#!/usr/bin/env python3
"""Smoke-test the parler TTS path before committing to a long render.

    # inside WSL, with .venv-tts active:
    python tools/tts_check.py

ParlerRenderer was written from the model card and has never executed - torch would not load on
the Windows side. This renders one short line per language and reports duration and file size,
so a broken call surfaces in minutes rather than eight hours into a full pre-render.
"""

import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SAMPLES = {
    "en": "You are eligible to convert purchases into easy monthly instalments.",
    "hi": "आप अपनी खरीदारी को आसान मासिक किस्तों में बदल सकते हैं।",
    "mr": "तुम्ही तुमची खरेदी सोप्या मासिक हप्त्यांमध्ये बदलू शकता.",
    "gu": "તમે તમારી ખરીદીને સરળ માસિક હપ્તામાં ફેરવી શકો છો.",
    "bn": "আপনি আপনার কেনাকাটা সহজ মাসিক কিস্তিতে পরিবর্তন করতে পারেন।",
    "ta": "உங்கள் பர்ச்சேஸ்களை எளிய மாத தவணைகளாக மாற்றலாம்.",
    "te": "మీ పర్చేజ్‌లను సులభమైన నెలవారీ వాయిదాలుగా మార్చుకోవచ్చు.",
    "kn": "ನಿಮ್ಮ ಖರೀದಿಗಳನ್ನು ಸುಲಭ ಮಾಸಿಕ ಕಂತುಗಳಾಗಿ ಬದಲಾಯಿಸಬಹುದು.",
    "ml": "നിങ്ങളുടെ പർച്ചേസുകൾ എളുപ്പമുള്ള മാസ തവണകളാക്കി മാറ്റാം.",
}


def main():
    out = ROOT / "runs" / "tts_check"
    out.mkdir(parents=True, exist_ok=True)

    print("loading indic-parler-tts ...", flush=True)
    t0 = time.perf_counter()
    from engine.prerender import ParlerRenderer
    tts = ParlerRenderer()
    print(f"  loaded in {time.perf_counter() - t0:.0f}s  ·  {tts.sample_rate} Hz  "
          f"·  device {tts._device}\n", flush=True)

    only = sys.argv[1:] or list(SAMPLES)
    failed = []
    for locale in only:
        text = SAMPLES.get(locale)
        if not text:
            continue
        t0 = time.perf_counter()
        try:
            wav = tts.render_wav(text, locale)
        except Exception as exc:                                   # noqa: BLE001
            print(f"  {locale:8} FAILED  {type(exc).__name__}: {exc}", flush=True)
            failed.append(locale)
            continue
        path = out / f"{locale}.wav"
        path.write_bytes(wav)
        secs = (len(wav) - 44) / 2 / tts.sample_rate
        print(f"  {locale:8} {time.perf_counter() - t0:6.1f}s render  "
              f"{secs:5.1f}s audio  {len(wav) / 1e6:5.2f} MB  -> {path.name}", flush=True)

    print(f"\n  {len(only) - len(failed)}/{len(only)} languages rendered -> "
          f"{out.relative_to(ROOT)}")
    if failed:
        print(f"  failed: {', '.join(failed)}")
    print("\n  LISTEN to these before starting the full render. A model that emits audio is not")
    print("  the same as a model that emits correct Indic pronunciation, and eight hours is a")
    print("  long time to find out.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
