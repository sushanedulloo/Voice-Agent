#!/usr/bin/env python3
"""Colab bootstrap for the GPU render. Everything the notebook does that is not rendering.

    from tools import colab_env
    colab_env.gpu()                      # what card did we get
    colab_env.install()                  # build-time deps, Colab-aware
    colab_env.fetch_model()              # ai4bharat/indic-parler-tts, ~3.8 GB, gated
    cache = colab_env.drive_cache()      # render target on mounted Drive

WHY A MODULE AND NOT NOTEBOOK CELLS
-----------------------------------
A notebook is not a reviewable artefact. Logic that lives in cells cannot be imported, diffed
sensibly, linted or run from a terminal, and the version that ran is whatever happened to be in
the browser. Everything here is ordinary Python in the repo; notebooks/render_audio_colab.ipynb
is a nine-line driver that calls it. If Colab disappears tomorrow the render still runs.

STDLIB ONLY, DELIBERATELY. This module is imported before anything is installed.

RESIDENCY
---------
Colab's GPUs are not in India. Constraint 4 is about the RUNTIME path and this is a build step -
ADR-005 means the serving box plays files and loads no model - and no customer data is involved,
because slot-bearing spans are the one thing never pre-rendered. What does cross is the approved
script text. That is ours today (`synthetic-placeholder`) and SBI Card's the day a real BLC pack
arrives, which is a confidentiality question to settle before that render, not after. RISKS R-17.
Nothing here is Colab-specific by necessity: tools/prerender_audio.py runs on any GPU.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Pinned to match requirements-build.txt, which is the combination verified against all nine
# languages on 2026-09-17. parler-tts subclasses transformers internals, so its working range is
# narrow and "whatever is latest" is not a version.
TRANSFORMERS = "transformers==4.46.1"
PARLER = "parler-tts @ git+https://github.com/huggingface/parler-tts.git"
EXTRA = ["accelerate>=0.26.0", "sentencepiece", "protobuf", "soundfile", "pyyaml", "librosa"]

# NOT installed on Colab: torch and torchaudio.
#
# requirements-build.txt pins torch==2.5.1 + torchaudio==2.5.1 because a MISMATCHED PAIR breaks
# torchaudio's native extension and parler_tts will not import. Colab already ships a matched
# pair built against its own CUDA driver. Forcing 2.5.1 over it downloads ~2.5 GB, can land on a
# CUDA build the host driver does not match, and buys nothing the pin was protecting against.
# The pin means "matched", not "2.5.1 specifically" - Colab satisfies it already.
SKIP_TORCH_ON_COLAB = True

MODEL_REPO = "ai4bharat/indic-parler-tts"
MODEL_DIR = ROOT / "models" / MODEL_REPO.replace("/", "__")

# Colab's A100 is the 40 GB SXM part. Anything smaller still works - parler in bf16 is about
# 5 GB of weights - it just takes longer, so this is a note, not a gate.
EXPECTED_GPU = "A100"


def on_colab() -> bool:
    return "google.colab" in sys.modules or os.path.exists("/content")


def _run(cmd: list, **kw) -> int:
    print("  $", " ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""), flush=True)
    return subprocess.run(cmd, check=False, **kw).returncode


# --------------------------------------------------------------------------------------------
# 1. What hardware did we actually get
# --------------------------------------------------------------------------------------------

def gpu() -> dict:
    """Report the card. Colab hands out whatever is free, and the runtime type you picked is a
    request, not a guarantee - worth knowing before starting an hour-long job."""
    if not shutil.which("nvidia-smi"):
        print("  NO GPU. Runtime -> Change runtime type -> A100 GPU, then run this again.")
        print("  parler on CPU measured ~120 s per clip: 1,089 clips is about 36 hours.")
        return {}
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
         "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    name, memory, driver = (p.strip() for p in out.split(","))
    print(f"  {name}  ·  {memory}  ·  driver {driver}")
    if EXPECTED_GPU not in name:
        print(f"  note: this is not an {EXPECTED_GPU}. The render works; it takes longer.")
    return {"name": name, "memory": memory, "driver": driver}


# --------------------------------------------------------------------------------------------
# 2. Dependencies
# --------------------------------------------------------------------------------------------

def install(quiet: bool = True) -> None:
    """Install the build-time deps on top of whatever torch the host already has.

    Run this BEFORE anything in the session imports transformers. Colab pre-installs
    transformers but does not pre-import it, so installing first means no runtime restart; if
    something has already imported it, pip's replacement will not take effect until a restart
    and `verify()` will say so.
    """
    if not (on_colab() and SKIP_TORCH_ON_COLAB):
        print("  not on Colab - installing the full pinned set from requirements-build.txt")
        _run([sys.executable, "-m", "pip", "install", "-q" if quiet else "-v",
              "-r", str(ROOT / "requirements-build.txt")])
        return

    if "transformers" in sys.modules:
        print("  ! transformers is already imported in this session. pip will install the "
              "pinned version but this kernel keeps the old one.\n"
              "  ! Runtime -> Restart session, then run this cell again before any import.")

    args = [sys.executable, "-m", "pip", "install"]
    if quiet:
        args.append("-q")
    _run(args + [TRANSFORMERS, PARLER, *EXTRA])
    print("  torch left alone on purpose - see SKIP_TORCH_ON_COLAB in tools/colab_env.py")


def verify() -> bool:
    """Import the whole stack and print versions. Two minutes here beats a failure at clip 40."""
    ok = True
    try:
        import torch
        print(f"  torch        {torch.__version__}  ·  cuda {torch.version.cuda}  ·  "
              f"available {torch.cuda.is_available()}  ·  bf16 "
              f"{torch.cuda.is_available() and torch.cuda.is_bf16_supported()}")
        import torchaudio
        print(f"  torchaudio   {torchaudio.__version__}")
        import transformers
        print(f"  transformers {transformers.__version__}")
        if not transformers.__version__.startswith(TRANSFORMERS.split("==")[1]):
            print(f"  ! expected {TRANSFORMERS} - restart the session and re-run install()")
            ok = False
        import parler_tts                                            # noqa: F401
        print("  parler_tts   imported")
    except Exception as exc:                                         # noqa: BLE001
        print(f"  FAILED {type(exc).__name__}: {exc}")
        ok = False
    return ok


# --------------------------------------------------------------------------------------------
# 3. Weights
# --------------------------------------------------------------------------------------------

def fetch_model(token: str | None = None) -> pathlib.Path:
    """Pull indic-parler-tts into models/, where ParlerRenderer expects it.

    Only the TTS model, not tools/fetch_models.py's full ~8 GB set: the ASR candidates are for
    the ADR-006 benchmark and have no part in rendering audio. Downloading them here would cost
    4 GB of a session that gets reclaimed.

    The repo is gated, so a token is required. Accepting the licence is a legal act on behalf of
    TransOrg and stays a human step - do it at huggingface.co/ai4bharat/indic-parler-tts first.
    """
    from huggingface_hub import snapshot_download
    token = token or os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit(
            "no HF_TOKEN. ai4bharat/indic-parler-tts is gated: accept the licence at\n"
            "  https://huggingface.co/ai4bharat/indic-parler-tts\n"
            "then add a read token to Colab Secrets as HF_TOKEN and enable it for this "
            "notebook.")
    if any(MODEL_DIR.glob("*.safetensors")):
        print(f"  already on disk: {MODEL_DIR}")
        return MODEL_DIR
    print(f"  downloading {MODEL_REPO} (~3.8 GB) ...", flush=True)
    snapshot_download(repo_id=MODEL_REPO, local_dir=str(MODEL_DIR), token=token)
    print(f"  -> {MODEL_DIR}")
    return MODEL_DIR


# --------------------------------------------------------------------------------------------
# 4. Where the output goes
# --------------------------------------------------------------------------------------------

def drive_cache(folder: str = "VoiceAgent-audio", mount: str = "/content/drive") -> pathlib.Path:
    """Mount Drive and point the render at it. Returns the cache root (the parent of wav/).

    RENDERING STRAIGHT TO DRIVE, not to local disk with a copy at the end: a Colab session can
    be reclaimed without warning, and the clips are the expensive thing. Written to Drive as
    they are produced, a session that dies at clip 700 has banked 700 clips - the content-
    addressed filename means the next run simply renders the remaining 389. A local render that
    dies before its zip step has produced nothing.

    The cost is a slower write per file. A WAV is ~130 kB against several seconds of generation,
    so it does not show up in the total.
    """
    if on_colab():
        from google.colab import drive                              # noqa: PLC0415
        if not os.path.ismount(mount):
            drive.mount(mount)
        cache = pathlib.Path(mount) / "MyDrive" / folder
    else:
        cache = ROOT / "audio_cache"
    (cache / "wav").mkdir(parents=True, exist_ok=True)
    # Both the tools and apps/server.py resolve the cache through engine.prerender, which reads
    # this. Setting it once here is what keeps the notebook from passing --cache everywhere.
    os.environ["VOICEAGENT_AUDIO_CACHE"] = str(cache)
    print(f"  cache -> {cache / 'wav'}")
    return cache


def secret(name: str) -> str | None:
    """Read a Colab secret, or fall back to the environment off-Colab.

    Secrets, never a literal in the notebook: the notebook is committed to the repo, and a token
    pasted into a cell is a token in git history forever.
    """
    if on_colab():
        try:
            from google.colab import userdata                       # noqa: PLC0415
            return userdata.get(name)
        except Exception:                                           # noqa: BLE001
            return os.environ.get(name)
    return os.environ.get(name)


if __name__ == "__main__":
    gpu()
    install()
    verify()
