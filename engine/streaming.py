"""Turn a stream of audio frames into utterances. Endpointing lives here.

DESIGN 2.1 puts the endpointing wait at 300-500 ms and calls it the largest single line in the
latency budget - larger than ASR, larger than the router, larger than anything a faster model
would buy back. Teams reach for a bigger GPU to fix a problem that lives in a silence threshold.
So it is its own module, with its numbers as named constants, and it is the first thing to tune
against real recordings.

The VAD here is energy-based. Silero (DESIGN's choice, ~1 ms, 8 kHz native) is a torch model and
torch will not load on this workstation, so this stands in. Energy VAD is genuinely worse in the
condition we care about - a noisy Indian street, a television, a second conversation in the room
- and it is the component most likely to be replaced first. It is marked accordingly.

What is NOT a stand-in is the shape: streaming frames in, endpointed utterances out, with the
thresholds as data. Swapping Silero in is one method.
"""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16000
FRAME_MS = 20                     # matches ptime 20 on the SIP leg (ADR-003)
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000

# Endpointing. These are the numbers to tune first, and tuning them is worth more than any
# model swap in the pipeline.
SILENCE_TO_ENDPOINT_MS = 450      # DESIGN 2.1 budgets 300-500 ms here
MIN_SPEECH_MS = 200               # shorter than this is a cough, a click, or crosstalk
MAX_UTTERANCE_MS = 15000          # hard stop; nobody says one useful sentence for 15 seconds

# Energy gate. Absolute RMS on float32 audio in [-1, 1].
SPEECH_RMS = 0.012
NOISE_FLOOR_ALPHA = 0.995         # slow-moving background estimate
NOISE_MARGIN = 2.5                # speech must exceed this multiple of the running floor


class Endpointer:
    """Feed it frames; it hands back a complete utterance when the customer stops.

    Also reports barge-in: speech detected while we are the one talking. DESIGN 2.3 makes the
    point that stopping TTS is only step 2 of 4 - on a real gateway, flushing the 200-400 ms
    already buffered downstream is what actually stops the caller hearing us.
    """

    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.noise_floor = 0.004
        self.reset()

    def reset(self):
        self._buffer = []
        self._speech_ms = 0
        self._silence_ms = 0
        self._in_speech = False

    @property
    def in_speech(self) -> bool:
        return self._in_speech

    def _is_speech(self, frame: np.ndarray) -> bool:
        rms = float(np.sqrt(np.mean(np.square(frame))) + 1e-9)
        if rms < SPEECH_RMS:
            # Only adapt the floor on frames we already believe are silence, so a long utterance
            # cannot drag the threshold up and cut itself off.
            self.noise_floor = (NOISE_FLOOR_ALPHA * self.noise_floor
                                + (1 - NOISE_FLOOR_ALPHA) * rms)
        return rms > max(SPEECH_RMS, self.noise_floor * NOISE_MARGIN)

    def push(self, frame: np.ndarray):
        """Returns (utterance | None, speech_started). Utterance is float32 at sample_rate."""
        frame_ms = len(frame) * 1000 // self.sample_rate
        speech = self._is_speech(frame)
        started = False

        if speech:
            if not self._in_speech:
                self._in_speech = True
                started = True
            self._speech_ms += frame_ms
            self._silence_ms = 0
            self._buffer.append(frame)
        elif self._in_speech:
            self._silence_ms += frame_ms
            self._buffer.append(frame)          # keep trailing silence; ASR needs the tail

        if not self._in_speech:
            return None, started

        done = (self._silence_ms >= SILENCE_TO_ENDPOINT_MS
                or self._speech_ms >= MAX_UTTERANCE_MS)
        if not done:
            return None, started

        audio = np.concatenate(self._buffer) if self._buffer else np.zeros(0, dtype=np.float32)
        too_short = self._speech_ms < MIN_SPEECH_MS
        self.reset()
        return (None if too_short else audio), started


def to_telephony(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Destroy the high band the way a G.711 leg does, then restore the sample rate.

    This is the demo that matters. Flip it on and the same sentence arrives as it would over an
    actual phone line - a quarter of the bandwidth - while the model still receives the shape it
    expects. Every published Indic STT number is measured on the audio this function throws away.
    """
    import librosa
    narrow = librosa.resample(audio, orig_sr=sample_rate, target_sr=8000)
    return librosa.resample(narrow, orig_sr=8000, target_sr=sample_rate)
