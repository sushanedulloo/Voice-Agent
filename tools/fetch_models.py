#!/usr/bin/env python3
"""Fetch the candidate speech models for the ADR-006 benchmark.

    python tools/fetch_models.py

Downloads weights only. Nothing here selects a model, and nothing here runs one - selection
happens against our own 8 kHz corpus, and none of these has a published number for that.

Licences are asserted from the model card at download time and recorded in models/MANIFEST.json,
because a licence is a commercial fact a bank's legal review will ask about and "I remember it
being MIT" is not an answer. A repo whose licence is not in ALLOWED is refused outright.
"""

import json
import pathlib
import sys

from huggingface_hub import HfApi, snapshot_download
from huggingface_hub.errors import GatedRepoError

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

# Commercially usable, no field-of-use restriction. XTTS-v2's "Coqui Public Model License" is
# deliberately absent - see engine/speech.py.
ALLOWED = {"mit", "apache-2.0", "bsd-3-clause", "cc-by-4.0"}

REPOS = [
    ("ai4bharat/indic-conformer-600m-multilingual", "asr",
     "Primary ASR candidate. 22 Indian languages, hybrid CTC+RNNT, streams natively."),
    ("ai4bharat/indic-parler-tts", "tts",
     "Primary TTS candidate. 21 Indian languages. Pre-rendered offline (ADR-005), "
     "so its latency is paid once per line and not once per call."),
    ("openai/whisper-large-v3-turbo", "asr",
     "Baseline the primary has to beat. Not Indic-specific; not natively streaming."),
    ("hexgrad/Kokoro-82M", "tts",
     "TTS fallback for en/hi only. 82M, unusually good quality per parameter."),
]


def main():
    api = HfApi()
    MODELS.mkdir(exist_ok=True)
    manifest, gated, failed = [], [], []

    for repo, role, note in REPOS:
        info = api.model_info(repo, files_metadata=True)
        licence = str((info.card_data or {}).get("license", "")).lower()
        size = sum(f.size or 0 for f in info.siblings)

        if licence not in ALLOWED:
            print(f"REFUSED {repo}: licence {licence!r} is not on the allowed list")
            continue

        print(f"\n{repo}  [{role}]  {licence}  {size / 1e9:.2f} GB")
        print(f"  {note}")
        target = MODELS / repo.replace("/", "__")
        # Already on disk (a gated repo fetched by hand, say). Record it, do not re-pull 3.6 GB.
        if any(target.glob("*.safetensors")) or any(target.glob("assets/*")):
            manifest.append({
                "repo": repo, "role": role, "license": licence,
                "sha": info.sha, "size_bytes": size,
                "local_path": str(target.relative_to(ROOT)), "note": note,
                "benchmarked_at_8khz": False, "source": "already present"})
            print("  already on disk, recorded")
            continue
        try:
            local = snapshot_download(repo_id=repo,
                                      local_dir=target)
        except GatedRepoError:
            # Gating is a different question from licensing. These weights ARE MIT/Apache, but
            # the repo additionally requires an authenticated account that has accepted the
            # terms. Accepting a licence agreement is a legal act on behalf of TransOrg, so it
            # is deliberately not automated here - a person does it, having read it.
            # And one gated repo must not abort the download of the others.
            print("  GATED - needs an accepted licence + `hf auth login`. Skipped.")
            gated.append(repo)
            continue
        except Exception as exc:                                   # noqa: BLE001
            print(f"  FAILED {type(exc).__name__}: {exc}")
            failed.append(repo)
            continue
        manifest.append({
            "repo": repo, "role": role, "license": licence,
            "sha": info.sha, "size_bytes": size,
            "local_path": str(pathlib.Path(local).relative_to(ROOT)),
            "note": note,
            "benchmarked_at_8khz": False,      # flips only when ADR-006 has actually run
        })
        print(f"  -> {local}")

    (MODELS / "MANIFEST.json").write_text(
        json.dumps({"downloaded": manifest, "gated": gated, "failed": failed}, indent=2),
        encoding="utf-8")
    if gated:
        print(f"\n  {len(gated)} gated, NOT downloaded - a person must accept the terms:")
        for repo in gated:
            print(f"    https://huggingface.co/{repo}")
        print("    then: hf auth login")
    if failed:
        print(f"\n  {len(failed)} failed: {', '.join(failed)}")
    print(f"\n{len(manifest)} models in {MODELS}")
    print("None benchmarked. Nothing selected. See docs/adr/ADR-006-measurement-first.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
