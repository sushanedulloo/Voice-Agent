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

# protobuf is a FLOOR, not a bare name, and the distinction is the whole reason this constant
# has a comment.
#
# Colab's preinstalled stack is generated against protobuf 5.x: its `_pb2.py` files begin with
# `from google.protobuf import runtime_version`, which only exists in protobuf >= 5.27. Several
# packages in parler-tts's dependency tree still declare an old protobuf ceiling, and pip's
# resolver satisfies that by silently DOWNGRADING the protobuf Colab is running on. pip reports
# success. The next import of anything protobuf-generated then dies with
#
#     cannot import name 'runtime_version' from 'google.protobuf'
#
# which reads like a transformers bug and is not one. A floor makes the resolver either honour
# it or fail loudly at install time, where the message is actionable.
PROTOBUF_FLOOR = "5.27"

EXTRA = ["accelerate>=0.26.0", "sentencepiece", f"protobuf>={PROTOBUF_FLOOR}",
         "soundfile", "pyyaml", "librosa"]

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
    """Run it, and SAY SO when it fails.

    This used to swallow the return code. pip installed transformers, failed on parler-tts,
    exited non-zero, and install() printed nothing and carried on - so the first sign of trouble
    was `ModuleNotFoundError: No module named 'parler_tts'` four cells later, in a traceback
    pointing at engine/prerender.py. A build step that reports success it did not have is worse
    than one that crashes.
    """
    print("  $", " ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""), flush=True)
    code = subprocess.run(cmd, check=False, **kw).returncode
    if code:
        print(f"  ! FAILED (exit {code}): {' '.join(cmd)}")
    return code


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

def _version(package: str):
    from importlib.metadata import PackageNotFoundError, version    # noqa: PLC0415
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def _older_than(have: str, floor: str) -> bool:
    def parts(v):
        return [int(x) for x in v.split(".")[:3] if x.isdigit()]
    return parts(have) < parts(floor)


def install(quiet: bool = True) -> bool:
    """Install the build-time deps on top of whatever torch the host already has.

    Returns True if the session must be RESTARTED before anything else will work.

    Run this before anything in the session imports transformers. Colab pre-installs it but does
    not pre-import it, so installing first usually avoids a restart. protobuf is different: it
    is already imported by the time a Colab session finishes booting, so if the resolver moves
    it, a restart is not optional.
    """
    if not (on_colab() and SKIP_TORCH_ON_COLAB):
        print("  not on Colab - installing the full pinned set from requirements-build.txt")
        _run([sys.executable, "-m", "pip", "install", "-q" if quiet else "-v",
              "-r", str(ROOT / "requirements-build.txt")])
        return False

    before = {name: _version(name) for name in ("protobuf", "transformers")}

    args = [sys.executable, "-m", "pip", "install"]
    if quiet:
        args.append("-q")

    # transformers and the extras first, parler-tts LAST and in its own call. parler-tts is a
    # git install with a heavy dependency tree (descript-audio-codec and friends) and it is by
    # far the most likely thing here to fail; on its own it fails by name instead of taking the
    # whole command down with it, and the retry below is not quiet.
    _run(args + [TRANSFORMERS, *EXTRA])
    if _run(args + [PARLER]):
        print("  ! retrying parler-tts with full output - the error above is truncated by -q")
        _run([sys.executable, "-m", "pip", "install", PARLER])
    print("  torch left alone on purpose - see SKIP_TORCH_ON_COLAB in tools/colab_env.py")

    # Belt and braces: the floor in EXTRA should prevent a downgrade, but a transitive pin
    # resolved in a later pass can still win. Check the outcome rather than trusting the input.
    have = _version("protobuf")
    if have and _older_than(have, PROTOBUF_FLOOR):
        print(f"  ! the dependency tree pulled protobuf back to {have}; Colab's own packages "
              f"need >= {PROTOBUF_FLOOR}. Repairing.")
        _run(args + [f"protobuf>={PROTOBUF_FLOOR}"])
        have = _version("protobuf")
        print(f"  protobuf now {have}")

    missing = [n for n in ("transformers", "parler-tts", "accelerate") if not _version(n)]
    if missing:
        print(f"\n  ! NOT INSTALLED: {', '.join(missing)}. Nothing below this will work - read "
              f"the pip output above before going on.")

    after = {"protobuf": have, "transformers": _version("transformers")}
    moved = [n for n in before if before[n] != after[n] and n in _loaded_roots()]
    if moved:
        print(f"\n  RESTART REQUIRED - {', '.join(moved)} changed underneath a module this "
              f"kernel has already imported.\n"
              f"  Call colab_env.restart(), then re-run from cell 1.")
    return bool(moved)


def _loaded_roots() -> set:
    """Top-level packages this kernel has already imported. protobuf lands here as
    `google.protobuf`, which is why this looks at prefixes rather than exact names."""
    loaded = set()
    for name in list(sys.modules):
        loaded.add(name.split(".")[0])
        if name.startswith("google.protobuf"):
            loaded.add("protobuf")
    return loaded


def restart() -> None:
    """Restart the Colab kernel. Everything in memory goes, including the repo on sys.path -
    which is why the instruction is always "re-run from cell 1" rather than "re-run this cell"."""
    print("  restarting - re-run from cell 1 once the kernel is back")
    import IPython                                                  # noqa: PLC0415
    IPython.get_ipython().kernel.do_shutdown(restart=True)


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
        print(f"  protobuf     {_version('protobuf')}")
        # Through engine.prerender, not a bare `import transformers`: prerender is what sets
        # USE_TF=0, and verifying under conditions the render will not have is not verifying.
        from engine import prerender                                 # noqa: F401
        import transformers
        print(f"  transformers {transformers.__version__}")
        if not transformers.__version__.startswith(TRANSFORMERS.split("==")[1]):
            print(f"  ! expected {TRANSFORMERS} - restart the session and re-run install()")
            ok = False
        print(f"  tensorflow   {'disabled (USE_TF=0)' if os.environ.get('USE_TF') == '0' else 'ENABLED - see engine/prerender.py'}")
        # Force the lazy module that actually pulls the TF/protobuf chain in. Without this,
        # verify() passes and the failure surfaces later, inside the render, wearing a different
        # hat - a TTS load that dies in an object-detection loss import.
        from transformers import modeling_utils                      # noqa: F401
        import parler_tts                                            # noqa: F401
        print("  parler_tts   imported")
    except Exception as exc:                                         # noqa: BLE001
        print(f"  FAILED {type(exc).__name__}: {exc}")
        _explain(exc)
        ok = False
    return ok


def _explain(exc: Exception) -> None:
    """Turn the two failures this stack actually produces into instructions.

    Both of them point at transformers and neither is a transformers problem, so the raw
    traceback sends you to the wrong place.
    """
    text = str(exc)
    if "runtime_version" in text and "protobuf" in text:
        have = _version("protobuf")
        print(f"\n  TensorFlow, not transformers and not protobuf on its own. The chain is:\n")
        print("      parler_tts -> transformers.modeling_utils -> loss_deformable_detr")
        print("        -> image_transforms -> `import tensorflow` -> attr_value_pb2\n")
        print(f"  Colab's TensorFlow is generated against protobuf >= {PROTOBUF_FLOOR}; "
              f"installed is {have},\n  because parler-tts's tree pins it lower. Nothing in our "
              f"path needs TensorFlow.\n")
        print("  engine/prerender.py sets USE_TF=0 to stop transformers looking for it. Seeing "
              "this\n  means it was imported before that ran, or the checkout is stale:\n")
        print(f"      !pip install -q 'protobuf>={PROTOBUF_FLOOR}'")
        print("      colab_env.restart()        # then re-run from cell 1")
        print("\n  The restart is not optional - protobuf and transformers are already in "
              "sys.modules,\n  and a reinstall does not touch a module this kernel has loaded.")
    elif "torchaudio" in text or "torio" in text:
        print("\n  torch and torchaudio are a mismatched pair - the native extension will not "
              "load\n  and parler_tts cannot import. Do not install one without the other.")


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
