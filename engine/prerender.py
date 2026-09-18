"""ADR-005: render every fixed approved line once, offline. Play the file at call time.

The set of utterances is finite and known ahead of time (ADR-002), which hands us an option most
voice agents do not have: the audio can be produced once instead of on every call. At 20.4 lakh
conversations a month, synthesising at runtime means paying to re-speak the identical
BLC-approved sentence two million times.

WHAT THIS MODULE ACTUALLY CONTRIBUTES
-------------------------------------
cost_model.py carries `PRERENDERED_SHARE = 0.80` as an assumption. That number drives the TTS
line in the direct cost, and nobody measured it. This module computes it from the content pack:
it splits every approved line into fixed spans and `{slot}` spans, weights them by spoken
character count, and reports what fraction of speech is genuinely cacheable.

An assumption replaced by a measurement is worth more than the code around it.

CACHE KEY
---------
sha256(text + locale + voice + engine + engine_version). Text, not utterance id - two nodes that
say the same sentence share one audio file, and a line whose wording changes gets a new key
automatically rather than silently playing the old approval. The cache is keyed by what is
spoken, so it cannot drift from what was approved.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parent.parent

# THE one definition of where audio lives. apps/server.py, tools/prerender_audio.py and
# tools/render_status.py all resolve through here rather than each rebuilding the path, so a
# render that writes somewhere else cannot silently disagree with a server that reads the
# default.
#
# The env var exists for exactly one case: rendering on a borrowed machine whose local disk is
# ephemeral. On Colab the cache points at a mounted Drive folder, so a session that dies at clip
# 700 loses nothing. See notebooks/render_audio_colab.ipynb.
CACHE = pathlib.Path(os.environ.get("VOICEAGENT_AUDIO_CACHE") or (ROOT / "audio_cache"))
WAV_CACHE = CACHE / "wav"
INDEX_NAME = "INDEX.json"

SLOT = re.compile(r"(\{[a-z_]+\})")

# Peak-normalisation target for rendered audio.
#
# WHY: measured across the nine languages, parler's output level varies by ~3.5x - Telugu came
# back at 0.24 peak against ~0.9 for the rest. Nothing is broken, the model just renders some
# languages quieter. On an 8 kHz telephony leg that is the difference between clearly audible
# and "can you speak up", and it would vary by the customer's language, which is indefensible.
#
# Peak rather than RMS/LUFS deliberately: these are short spans played back to back, and RMS
# normalisation would pump the quiet ones (a two-word span of silence-plus-a-number) to the same
# loudness as a full sentence. Peak keeps the dynamics and just fixes the level.
NORMALISE_PEAK = 0.85


def normalise(audio):
    """Bring a clip to a consistent peak level. No-op on silence."""
    import numpy as np
    a = np.asarray(audio, dtype="float32")
    peak = float(np.max(np.abs(a))) if a.size else 0.0
    if peak < 1e-4:
        return a
    return a * (NORMALISE_PEAK / peak)


@dataclass
class Span:
    text: str
    fixed: bool          # False means it carries a campaign variable and must be live

    @property
    def chars(self) -> int:
        return len(self.text.strip())


@dataclass
class Utterance:
    id: str
    kind: str            # node | disclosure | faq
    locale: str
    raw: str
    spans: list = field(default_factory=list)

    @property
    def fixed_chars(self) -> int:
        return sum(s.chars for s in self.spans if s.fixed)

    @property
    def live_chars(self) -> int:
        return sum(s.chars for s in self.spans if not s.fixed)


def split_spans(text: str) -> list:
    """Fixed prose and {slot} spans, in order.

    Splitting mid-sentence is what makes this work: "your instalment would be about {x} rupees"
    is one live number surrounded by two cacheable spans, not one uncacheable sentence. Naively
    treating any line containing a slot as live would throw away most of the saving.
    """
    return [Span(part, not (part.startswith("{") and part.endswith("}")))
            for part in SLOT.split(text) if part.strip()]


def enumerate_utterances(content) -> list:
    """Every string the bot can ever say, per locale. If it is not in here, it cannot be said."""
    out = []
    for locale in content.locales:
        for product in content.products.values():
            for node in product.nodes.values():
                text = (node.line or {}).get(locale, "")
                if text.strip():
                    out.append(Utterance(node.id, "node", locale, text, split_spans(text)))
        for did, spec in content.disclosures.items():
            text = " ".join(spec["line"][locale].split())
            out.append(Utterance(did, "disclosure", locale, text, split_spans(text)))
        for fid, entry in content.faq.items():
            text = entry.answer.get(locale, "")
            if text.strip():
                out.append(Utterance(fid, "faq", locale, text, split_spans(text)))
    return out


def cache_key(text: str, locale: str, voice: str, engine: str, version: str) -> str:
    h = hashlib.sha256()
    for part in (text.strip(), locale, voice, engine, version):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:24]


# --------------------------------------------------------------------------------------------
# The render plan, and the index the serving box reads.
#
# Both of these used to be written out twice - once in tools/prerender_audio.py and once in
# tools/render_status.py. Two copies of "what should exist" is one copy too many: the moment
# they drift, the status tool reports a complete render that the server cannot serve.
# --------------------------------------------------------------------------------------------

def plan(content, *, engine: str, version: str, voice: str = "default",
         locales=None) -> dict:
    """Every clip that must exist, as {cache_key: (locale, text)}.

    This is the whole definition of "done". Deduplicated by key, so a sentence shared by two
    nodes appears once - which is also why the count is lower than the utterance count.
    """
    wanted = {}
    keep = set(locales) if locales else None
    for utt in enumerate_utterances(content):
        if keep is not None and utt.locale not in keep:
            continue
        for span in utt.spans:
            text = span.text.strip()
            if not span.fixed or not text:
                continue
            wanted[cache_key(text, utt.locale, voice, engine, version)] = (utt.locale, text)
    return wanted


def outstanding(wanted: dict, cache: pathlib.Path) -> dict:
    """The subset of `wanted` not yet on disk. This is the resume protocol, in full.

    There is nothing else to it because the filename IS the hash of what is spoken: a half
    finished render leaves correct, complete files, never a partial one, and re-running picks up
    exactly where it stopped without any shared state.
    """
    return {k: v for k, v in wanted.items() if not (cache / f"{k}.wav").exists()}


def index_entry(locale: str, voice: str, text: str) -> str:
    """The key apps/server.py looks up: what is spoken, not which engine spoke it."""
    return f"{locale}\u241f{voice}\u241f{text}"


def load_index(cache: pathlib.Path) -> dict:
    path = cache / INDEX_NAME
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_index(cache: pathlib.Path, wanted: dict, *, content, renderer,
                voice: str = "default") -> int:
    """Point the serving box at whatever is now on disk.

    INDEX.json is what makes ADR-005 actually hold: the server looks audio up by WHAT IS SPOKEN
    (text + locale + voice), never by which engine rendered it. Without this the server has to
    instantiate a TTS engine just to compute a filename - which would mean shipping torch to
    production to play files that were rendered offline weeks earlier.

    Merges rather than replaces, so a machine that rendered five locales does not delete the
    four another machine rendered.
    """
    spans = load_index(cache).get("spans", {})
    for key, (locale, text) in wanted.items():
        if (cache / f"{key}.wav").exists():
            spans[index_entry(locale, voice, text)] = f"{key}.wav"
    (cache / INDEX_NAME).write_text(json.dumps(
        {"engine": renderer.name, "engine_version": renderer.version,
         "sample_rate": renderer.sample_rate, "voice": voice,
         "pack": content.pack_name, "content_hash": content.content_hash,
         "spans": spans}, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(spans)


def wav_bytes(audio, sample_rate: int) -> bytes:
    """Normalised float audio -> a WAV a browser can play. One definition, used by every
    renderer, so a new engine cannot quietly ship a different header or bit depth."""
    import io
    import soundfile as sf
    buf = io.BytesIO()
    sf.write(buf, normalise(audio), sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _stable_seed(base: int, text: str) -> int:
    """A seed derived from the content, not from the process.

    Deliberately not `hash()`: Python salts string hashing per process, so a seed built on it
    would be reproducible only within one run - the opposite of what a reproducible render
    needs. sha256 of the text is the same on every machine, forever.
    """
    if not text:
        return base
    digest = hashlib.sha256(text.encode("utf-8")).digest()[:4]
    return (base ^ int.from_bytes(digest, "big")) & 0x7FFFFFFF


def trim_trailing_silence(audio, sample_rate: int, threshold: float = 2e-3,
                          keep_ms: int = 60):
    """Drop the padding a batched decode leaves on the end of the shorter clips.

    Batched generation pads every row out to the longest in the batch. Left alone, a two-word
    span batched with a full sentence carries four seconds of silence, and the bot sounds like
    it is thinking between every phrase. `keep_ms` leaves a natural tail rather than clipping
    the last consonant.
    """
    import numpy as np
    a = np.asarray(audio, dtype="float32")
    loud = np.flatnonzero(np.abs(a) > threshold)
    if loud.size == 0:
        return a[:0]
    end = min(a.size, int(loud[-1]) + 1 + int(sample_rate * keep_ms / 1000))
    return a[:end]


class SilentRenderer:
    """Stand-in renderer. Produces correctly-shaped silent PCM and nothing else.

    ai4bharat/indic-parler-tts needs PyTorch, which Windows Application Control blocks on this
    workstation (see engine/asr_engines.py). Rather than pretend, this renders silence of the
    right duration so the pipeline, the cache, the keying and the share measurement are all real
    and testable, and swapping in the real voice is one class.

    Duration is estimated from CHARS_PER_SEC in cost_model.py, so even the placeholder audio has
    a defensible length rather than an invented one.
    """

    name = "silent-stub"
    version = "0"
    sample_rate = 16000
    india_resident = True
    produces_audio = False           # the flag that stops this being mistaken for a voice

    def render(self, text: str, locale: str, voice: str = "default") -> bytes:
        import cost_model as cm
        seconds = max(len(text) / cm.CHARS_PER_SEC, 0.15)
        return b"\x00\x00" * int(self.sample_rate * seconds)

    def render_wav(self, text: str, locale: str, voice: str = "default") -> bytes:
        """Silence, correctly shaped. Lets tools/prerender_audio.py be exercised end to end on a
        machine with no model - the run is real, only the audio is not. `produces_audio = False`
        is what stops the result being mistaken for a voice: the tool refuses to write an
        INDEX.json from it, so this can never reach a caller."""
        import numpy as np
        import cost_model as cm
        seconds = max(len(text) / cm.CHARS_PER_SEC, 0.15)
        return wav_bytes(np.zeros(int(self.sample_rate * seconds), dtype="float32"),
                         self.sample_rate)


class KokoroRenderer:
    """Real neural TTS. Kokoro-82M via onnxruntime - no PyTorch, nothing leaves the machine.

    Chosen over ai4bharat/indic-parler-tts for one reason only: parler needs PyTorch, which
    Windows Application Control blocks here. Parler covers 21 Indian languages against Kokoro's
    handful, so when torch is available on the build box parler is the better answer for the
    full nine-language set. Kokoro covers en and hi, which is exactly the two locales the pack
    currently populates.

    NOT used: naklitechie/indic-parler-tts-ONNX. An unverified re-export from an account with
    85 downloads and no track record, whose decoder is 3.4 MB against a 3.76 GB source. That is
    a supply-chain question we should not be answering in front of a bank's security review.
    """

    name = "kokoro-82m-onnx"
    version = "1.0"
    sample_rate = 24000
    india_resident = True          # runs on our hardware
    produces_audio = True

    # Kokoro's own language tags, not our locale codes.
    LANG = {"en": "en-us", "hi_latn": "hi"}
    VOICE = {"en": "af_heart", "hi_latn": "hf_alpha"}

    def __init__(self, model=None, voices=None):
        from kokoro_onnx import Kokoro
        base = ROOT / "models" / "kokoro-onnx"
        self._k = Kokoro(str(model or base / "onnx" / "model.onnx"),
                         str(voices or base / "voices.npz"))

    def voice_for(self, locale: str, voice: str = "default") -> str:
        return self.VOICE.get(locale, "af_heart") if voice == "default" else voice

    def render(self, text: str, locale: str, voice: str = "default") -> bytes:
        audio, _ = self._k.create(text, voice=self.voice_for(locale, voice),
                                  speed=1.0, lang=self.LANG.get(locale, "en-us"))
        import numpy as np
        return (np.clip(normalise(audio), -1, 1) * 32767).astype(np.int16).tobytes()

    def render_wav(self, text: str, locale: str, voice: str = "default") -> bytes:
        """Same audio, wrapped in a WAV header so a browser can play it directly."""
        audio, sr = self._k.create(text, voice=self.voice_for(locale, voice),
                                   speed=1.0, lang=self.LANG.get(locale, "en-us"))
        return wav_bytes(audio, sr)


class ParlerRenderer:
    """ai4bharat/indic-parler-tts. The right answer for all nine languages.

    WHY THIS IS NOT THE DEFAULT YET: it needs PyTorch, and Windows Application Control blocks
    PyTorch's DLLs on the workstation this was built on. Kokoro was chosen only because it has
    an ONNX build; it is not a quality judgement and it covers two of our nine languages.

    WHY THAT MATTERS LESS THAN IT SOUNDS: ADR-005 renders every approved line offline, once.
    The serving box plays WAV files and never loads a TTS model at all. So torch is needed on
    ANY machine, ONCE, to produce audio_cache/wav - then the cache ships and the runtime never
    sees PyTorch. A blocked workstation is an inconvenience, not an architectural problem.

        # on any box where torch runs:
        pip install torch transformers git+https://github.com/huggingface/parler-tts
        python tools/prerender_audio.py --engine parler --locales en hi ta te kn ml mr gu bn
        # then copy audio_cache/wav across

    NOT USED: facebook/mms-tts-*, which covers every Indian language and is ONNX-exportable -
    but it is CC-BY-NC-4.0. Non-commercial licensing is not a detail a bank's legal review
    will wave through, and discovering it after building on it would be expensive.

    VERIFIED 2026-09-17 in WSL: all nine languages render, ~120 s per ~6 s clip on 4 CPU cores
    (RTF ~20). Needs torch 2.5.1 + torchaudio 2.5.1 - a mismatched pair breaks torchaudio's
    native extension and parler_tts will not import.

    ON A GPU: `render_wav_batch` decodes several spans in one forward pass, which is where
    almost all of the speedup lives - a single clip leaves an A100 mostly idle because the
    batch dimension is 1. See notebooks/render_audio_colab.ipynb.
    """

    name = "indic-parler-tts"
    version = "1.0"
    sample_rate = 44100
    india_resident = True
    produces_audio = True

    # parler is prompted in English with a description of the voice it should produce.
    DESCRIPTION = ("Priya speaks in a clear, warm, professional tone, at a moderate pace, "
                   "with very close recording that has no background noise.")
    LANG_NAME = {"en": "English", "hi": "Hindi", "hi_latn": "Hindi", "ta": "Tamil",
                 "te": "Telugu", "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi",
                 "gu": "Gujarati", "bn": "Bengali"}

    def __init__(self, model_dir=None, device=None, dtype=None, seed: int = 0):
        import torch
        from transformers import AutoTokenizer
        from parler_tts import ParlerTTSForConditionalGeneration
        base = str(model_dir or ROOT / "models" / "ai4bharat__indic-parler-tts")
        self._torch = torch
        self._device = device or ("cuda:0" if torch.cuda.is_available() else "cpu")
        self._dtype = self._resolve_dtype(torch, dtype)

        # parler samples (do_sample=True, temperature 1.0), so the same line rendered twice is
        # not the same audio. For a cache of BLC-approved clips that is not acceptable on its
        # own terms - "which render is this?" has to have an answer. Seeding per batch from the
        # cache keys makes a re-render of the same spans reproduce bit-for-bit.
        self._seed = seed
        self._dict_generate = True      # flipped off if this build rejects it; see _generate
        # low_cpu_mem_usage loads shard-by-shard instead of materialising the whole state dict
        # twice, which roughly halves the load peak - that peak is what the Linux OOM killer
        # caught in WSL ("Terminated", no traceback).
        #
        # It needs `accelerate`. Degrade rather than refuse: a missing optional dependency
        # should cost memory headroom, not stop the render entirely. The warning is loud because
        # without it two parallel workers may not fit.
        # sdpa is torch's own fused attention - no extra dependency, no flash-attn build, and
        # it is the difference between a GPU render that is worth doing and one that is not.
        kwargs = {"torch_dtype": self._dtype, "attn_implementation": "sdpa"}
        try:
            self._model = ParlerTTSForConditionalGeneration.from_pretrained(
                base, low_cpu_mem_usage=True, **kwargs).to(self._device)
        except ImportError:
            print("  ! accelerate not installed - loading without low_cpu_mem_usage. "
                  "Load peak roughly doubles. Run `pip install accelerate` if a worker "
                  "gets OOM-killed, or render one locale set at a time.")
            self._model = ParlerTTSForConditionalGeneration.from_pretrained(
                base, **kwargs).to(self._device)
        self._model.eval()
        self._tok = AutoTokenizer.from_pretrained(base)

        # The description tokenizer. parler's own example resolves this via
        # config.text_encoder._name_or_path, which is "google/flan-t5-large" - a HUB FETCH, at
        # render time, even though this repo already bundles the tokenizer locally.
        #
        # A build step that silently reaches the internet is not reproducible, will not run on
        # an air-gapped box, and drags a second upstream repo into the supply chain for files we
        # already have. Local first; the Hub only as a loud fallback.
        try:
            self._desc_tok = AutoTokenizer.from_pretrained(base, local_files_only=True)
        except Exception as exc:                                   # noqa: BLE001
            remote = self._model.config.text_encoder._name_or_path
            print(f"  ! local description tokenizer unavailable ({type(exc).__name__}); "
                  f"falling back to the Hub: {remote}")
            self._desc_tok = AutoTokenizer.from_pretrained(remote)

        self.sample_rate = self._model.config.sampling_rate

    @staticmethod
    def _resolve_dtype(torch, requested):
        """bf16 on Ampere and later, fp32 otherwise.

        Not fp16: parler's T5 description encoder and the DAC audio decoder both overflow in
        fp16 and the failure mode is silence or static, not an exception - which on a 1,089 clip
        unattended run means discovering it at the end. bf16 has fp32's exponent range, so it
        does not have that failure mode, and every GPU worth renting for this supports it.
        """
        if isinstance(requested, str) and requested != "auto":
            return getattr(torch, requested)
        if requested is not None and not isinstance(requested, str):
            return requested
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
            return torch.bfloat16
        return torch.float32

    def _describe(self, locale: str) -> str:
        return f"{self.DESCRIPTION} The language is {self.LANG_NAME.get(locale, 'Hindi')}."

    def _generate(self, items: list, seed_from: str = ""):
        """items: [(text, locale), ...] -> [float32 waveform, ...] in the same order.

        One description per row, so a batch may mix languages freely - which matters, because
        grouping strictly by locale would leave the last, ragged batch of every language running
        at batch size 2.
        """
        import numpy as np
        torch = self._torch
        texts = [t for t, _ in items]
        descriptions = [self._describe(loc) for _, loc in items]

        d = self._desc_tok(descriptions, return_tensors="pt", padding=True).to(self._device)
        p = self._tok(texts, return_tensors="pt", padding=True).to(self._device)

        kwargs = dict(input_ids=d.input_ids, attention_mask=d.attention_mask,
                      prompt_input_ids=p.input_ids, prompt_attention_mask=p.attention_mask)

        torch.manual_seed(_stable_seed(self._seed, seed_from))
        with torch.no_grad():
            # return_dict_in_generate gets us audios_length, which is the exact number of
            # samples in each row before padding. Not every parler build accepts it, and an
            # eight-hundred-clip unattended run is the wrong place to find that out, so a
            # rejection downgrades to the plain call and the trimmer below covers the gap.
            if self._dict_generate:
                try:
                    out = self._model.generate(**kwargs, return_dict_in_generate=True)
                except TypeError:
                    self._dict_generate = False
                    print("  note: this parler build does not accept "
                          "return_dict_in_generate; trimming batch padding by amplitude")
            if not self._dict_generate:
                out = self._model.generate(**kwargs)

        audio = getattr(out, "sequences", out)
        lengths = getattr(out, "audios_length", None)
        audio = audio.to(torch.float32).cpu().numpy()
        if audio.ndim == 1:
            audio = audio[None, :]
        audio = audio.reshape(len(items), -1)

        if lengths is not None:
            lengths = np.asarray(lengths.cpu() if hasattr(lengths, "cpu") else lengths).ravel()

        clips = []
        for i in range(len(items)):
            row = audio[i]
            if lengths is not None and i < lengths.size:
                row = row[:int(lengths[i])]
            elif len(items) > 1:
                row = trim_trailing_silence(row, self.sample_rate)
            clips.append(row)
        return clips

    def _audio(self, text: str, locale: str):
        return self._generate([(text, locale)], seed_from=text)[0]

    def render(self, text: str, locale: str, voice: str = "default") -> bytes:
        import numpy as np
        a = normalise(self._audio(text, locale))
        return (np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes()

    def render_wav(self, text: str, locale: str, voice: str = "default") -> bytes:
        return wav_bytes(self._audio(text, locale), self.sample_rate)

    def render_wav_batch(self, items: list, voice: str = "default") -> list:
        """The GPU path. items: [(text, locale), ...] -> [wav bytes, ...], same order."""
        clips = self._generate(items, seed_from="".join(t for t, _ in items))
        return [wav_bytes(c, self.sample_rate) for c in clips]


RENDERERS = {"kokoro": KokoroRenderer, "parler": ParlerRenderer, "silent": SilentRenderer}


def get_renderer(name: str = "kokoro"):
    if name not in RENDERERS:
        raise KeyError(f"unknown TTS engine {name!r}; have {sorted(RENDERERS)}")
    return RENDERERS[name]()


def build(content, renderer=None, cache_dir=None, voice: str = "default") -> dict:
    """Render every fixed span once. Returns the manifest, including the measured share."""
    renderer = renderer or SilentRenderer()
    cache = pathlib.Path(cache_dir or CACHE)
    cache.mkdir(parents=True, exist_ok=True)

    utterances = enumerate_utterances(content)
    entries, seen = {}, {}
    fixed_chars = live_chars = 0
    reused = 0

    for utt in utterances:
        fixed_chars += utt.fixed_chars
        live_chars += utt.live_chars
        for span in utt.spans:
            if not span.fixed:
                continue
            key = cache_key(span.text, utt.locale, voice, renderer.name, renderer.version)
            if key in seen:
                reused += 1
                continue
            path = cache / f"{key}.pcm"
            if not path.exists():
                path.write_bytes(renderer.render(span.text, utt.locale, voice))
            seen[key] = True
            entries[key] = {"text": span.text, "locale": utt.locale,
                            "utterance": utt.id, "kind": utt.kind,
                            "bytes": path.stat().st_size}

    total = fixed_chars + live_chars
    manifest = {
        "content_pack": content.pack_name,
        "content_hash": content.content_hash,
        "engine": renderer.name,
        "engine_version": renderer.version,
        "produces_audio": getattr(renderer, "produces_audio", True),
        "voice": voice,
        "locales": list(content.locales),
        "utterances": len(utterances),
        "cached_spans": len(entries),
        "deduplicated_spans": reused,
        "fixed_chars": fixed_chars,
        "live_chars": live_chars,
        # The number cost_model.py currently assumes as PRERENDERED_SHARE.
        "measured_prerendered_share": round(fixed_chars / total, 4) if total else 0.0,
        "entries": entries,
    }
    (cache / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest
