"""Concrete ASR engines behind the `ASR` protocol in speech.py.

IndicConformer runs here on onnxruntime and numpy alone - no PyTorch. That was forced rather
than chosen: Windows Application Control blocks torch's DLLs on this workstation. It turned out
to be the better shape anyway. The serving path now needs onnxruntime (~200 MB) instead of torch
(~2.5 GB), starts cold in a fraction of the time, and gives a bank's InfoSec review one large
unsigned dependency to assess instead of two.

    THE CAVEAT THAT MATTERS
    -----------------------
    The model ships its mel front-end as TorchScript (assets/preprocessor.ts). Since torch will
    not load here, MelFrontend below REIMPLEMENTS it from NeMo's documented parameters. Feature
    extraction that is subtly wrong does not crash - it quietly costs accuracy, and the blame
    lands on the model. So every engine carries `validated`, it is False until
    tools/validate_preprocessor.py has compared this front-end against preprocessor.ts on a
    machine where torch runs, and tools/benchmark_asr.py refuses to call any number
    decision-grade while it is False.

    An unvalidated front-end is fine for wiring the system together. It is not fine for choosing
    a component, and the difference is the whole of ADR-006.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"

# NeMo AudioToMelSpectrogramPreprocessor defaults for Conformer. Each is named with the NeMo
# keyword it mirrors so a reviewer can check them one by one against the model's config.
SAMPLE_RATE = 16000        # sample_rate
N_FFT = 512                # n_fft
WIN_LENGTH = 400           # window_size 0.025 s * 16000
HOP_LENGTH = 160           # window_stride 0.010 s * 16000
N_MELS = 80                # features
PREEMPH = 0.97             # preemph
LOG_ZERO_GUARD = 2 ** -24  # log_zero_guard_value, 'add'
PAD_TO = 16                # pad_to - time dimension padded up to a multiple of this


class MelFrontend:
    """80-bin log-mel, per-feature normalised. Reimplementation - see module caveat."""

    def __init__(self):
        import librosa
        self.filters = librosa.filters.mel(
            sr=SAMPLE_RATE, n_fft=N_FFT, n_mels=N_MELS, fmin=0.0, fmax=SAMPLE_RATE / 2)
        self.window = np.hanning(WIN_LENGTH + 1)[:-1].astype(np.float32)

    def __call__(self, audio: np.ndarray) -> np.ndarray:
        audio = np.asarray(audio, dtype=np.float32)
        # pre-emphasis, applied before framing exactly as NeMo does
        audio = np.concatenate([audio[:1], audio[1:] - PREEMPH * audio[:-1]])

        frames = 1 + (len(audio) - WIN_LENGTH) // HOP_LENGTH if len(audio) >= WIN_LENGTH else 1
        padded = np.pad(audio, (0, max(0, (frames - 1) * HOP_LENGTH + WIN_LENGTH - len(audio))))
        strided = np.lib.stride_tricks.as_strided(
            padded, shape=(frames, WIN_LENGTH),
            strides=(padded.strides[0] * HOP_LENGTH, padded.strides[0])) * self.window

        spec = np.abs(np.fft.rfft(strided, n=N_FFT, axis=-1)) ** 2.0     # mag_power = 2.0
        mel = self.filters @ spec.T
        mel = np.log(mel + LOG_ZERO_GUARD)

        # normalize='per_feature': zero mean, unit variance per mel bin, per utterance
        mean = mel.mean(axis=1, keepdims=True)
        std = mel.std(axis=1, keepdims=True)
        mel = (mel - mean) / (std + 1e-5)

        if mel.shape[1] % PAD_TO:
            mel = np.pad(mel, ((0, 0), (0, PAD_TO - mel.shape[1] % PAD_TO)))
        return mel[np.newaxis, :, :].astype(np.float32)


class IndicConformerCTC:
    """ai4bharat/indic-conformer-600m-multilingual, CTC greedy decoding, ONNX only.

    CTC rather than RNNT deliberately for the benchmark: it is a single forward pass with no
    autoregressive loop, so it isolates acoustic quality from decoder search. RNNT is the one we
    would actually stream in production (it is why this model was chosen over Whisper) and it
    scores a little better, so treat CTC numbers as a floor.
    """

    name = "indic_conformer_ctc"
    sample_rate = SAMPLE_RATE
    india_resident = True          # runs on our hardware; no endpoint leaves the country
    validated = False              # see module caveat

    def __init__(self):
        import onnxruntime as ort
        base = MODELS / "ai4bharat__indic-conformer-600m-multilingual" / "assets"
        if not base.exists():
            raise FileNotFoundError(f"{base} missing - run tools/fetch_models.py")
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        self._encoder = ort.InferenceSession(str(base / "encoder.onnx"), opts,
                                             providers=["CPUExecutionProvider"])
        self._ctc = ort.InferenceSession(str(base / "ctc_decoder.onnx"), opts,
                                         providers=["CPUExecutionProvider"])
        self.vocab = json.loads((base / "vocab.json").read_text(encoding="utf-8"))
        self.masks = json.loads((base / "language_masks.json").read_text(encoding="utf-8"))
        self.blank_id = 256
        self.frontend = MelFrontend()

    @property
    def languages(self):
        # 22 scheduled Indian languages. English is NOT among them - our en traffic needs a
        # different engine, which is a two-model ASR split rather than the one most decks assume.
        return sorted(self.vocab)

    def _encode(self, audio: np.ndarray):
        feats = self.frontend(audio)
        lengths = np.array([feats.shape[2]], dtype=np.int64)
        encoded, _ = self._encoder.run(["outputs", "encoded_lengths"],
                                       {"audio_signal": feats, "length": lengths})
        return self._ctc.run(["logprobs"], {"encoder_output": encoded})[0]

    def _decode(self, logprobs, language: str):
        lp = logprobs[:, :, self.masks[language]]          # 5633 -> this language's 257
        path = lp[0].argmax(axis=-1)
        collapsed = path[np.insert(np.diff(path) != 0, 0, True)]
        vocab = self.vocab[language]
        text = "".join(vocab[i] for i in collapsed
                       if i != self.blank_id).replace("▁", " ").strip()
        # Mean peak log-probability over non-blank frames. A language whose tokens actually fit
        # the audio produces confident peaks; a wrong one produces a flat, hedged path.
        peaks = lp[0].max(axis=-1)
        speech = path != self.blank_id
        score = float(peaks[speech].mean()) if speech.any() else float("-inf")
        return text, score

    def detect(self, audio: np.ndarray, candidates: list) -> tuple:
        """Transcribe in every candidate language from ONE encoder pass.

        This is the whole language-switching story. The 600M encoder costs ~585 ms and is shared
        across all 22 languages; each additional per-language head costs ~0.5 ms (measured). So
        deciding between nine languages costs 589 ms, not nine times 585 ms - language detection
        is effectively free, and it comes from the model's own architecture rather than a
        separate LID model in the hot path.

        UNVALIDATED, like the mel front-end: the scoring heuristic below has not been checked
        against real code-mixed telephony audio. It is the right shape; the threshold is not
        evidence. See ADR-006.
        """
        logprobs = self._encode(audio)
        scored = []
        for lang in candidates:
            if lang in self.vocab:
                text, score = self._decode(logprobs, lang)
                scored.append((lang, text, score))
        if not scored:
            return None, "", float("-inf"), []
        scored.sort(key=lambda r: -r[2])
        best = scored[0]
        return best[0], best[1], best[2], scored

    def transcribe(self, audio: np.ndarray, language: str) -> str:
        if language not in self.vocab:
            raise ValueError(f"{language!r} not in this model ({len(self.vocab)} languages, "
                             f"no English)")
        feats = self.frontend(audio)
        lengths = np.array([feats.shape[2]], dtype=np.int64)
        encoded, _ = self._encoder.run(["outputs", "encoded_lengths"],
                                       {"audio_signal": feats, "length": lengths})
        logprobs = self._ctc.run(["logprobs"], {"encoder_output": encoded})[0]
        logprobs = logprobs[:, :, self.masks[language]]          # 5633 -> this language's 257

        path = logprobs[0].argmax(axis=-1)
        collapsed = path[np.insert(np.diff(path) != 0, 0, True)]  # CTC collapse of repeats
        vocab = self.vocab[language]
        return "".join(vocab[i] for i in collapsed
                       if i != self.blank_id).replace("▁", " ").strip()


ENGINES = {IndicConformerCTC.name: IndicConformerCTC}


def available() -> list:
    """Engines whose weights are actually on disk. Not 'engines we like'."""
    out = []
    for name, cls in ENGINES.items():
        try:
            cls()
            out.append(name)
        except Exception:                                        # noqa: BLE001
            pass
    return out


def load_engine(name: str):
    if name not in ENGINES:
        raise KeyError(f"unknown engine {name!r}; have {sorted(ENGINES)}")
    return ENGINES[name]()
