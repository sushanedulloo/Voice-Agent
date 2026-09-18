"""The speech boundary. Two protocols and nothing else.

ADR-006: component choice is decided by measurement on our own 8 kHz corpus, never by a vendor
number or a model card. Nothing has been measured yet, so nothing is chosen yet. The cost of
holding that position honestly is this file: a boundary thin enough that swapping the
implementation is one class, not a refactor.

SELECTED, PENDING BENCHMARK  (a leaning, not a commitment - do not put these in a client document)

  ASR   ai4bharat/indic-conformer-600m    MIT · 22 Indian languages · 600M · hybrid CTC+RNNT.
                                          RNNT matters: it streams natively. Whisper does not,
                                          and chunking it into pseudo-streaming spends latency
                                          exactly where the budget is tightest.
        baseline to beat:                 openai/whisper-large-v3-turbo (MIT, 809M)

  TTS   ai4bharat/indic-parler-tts        21 Indian languages. ADR-005 pre-renders every fixed
                                          line offline, so its latency is paid once per line
                                          rather than once per call - which frees the choice to
                                          be about coverage and quality, not speed.
        fallback (en/hi only):            hexgrad/Kokoro-82M (Apache 2.0)

  RULED OUT
        coqui/XTTS-v2                     Coqui Public Model License, commercial terms not
                                          stated, upstream company defunct, and Hindi is its
                                          only Indian language. Licence risk with no upside.
        distil-whisper/distil-large-v3    English only.

  STILL UNCHOSEN, AND IT RUNS MORE OFTEN THAN EITHER OF THE ABOVE
        The router's embedding model (ADR-004) fires on EVERY turn, where ASR fires once per
        utterance and pre-rendered TTS never fires at all. It is currently a TF-IDF stand-in
        leaking 25% (tools/probe_router.py). Candidates - LaBSE, multilingual-e5, an
        IndicBERT-derived encoder - need the same benchmark treatment.

WHAT IS IMPLEMENTED TODAY
        Speech runs in the browser via the Web Speech API (apps/static/index.html). That is a
        harness: 16 kHz cloud ASR on Google's servers, which fails constraint 4 and says nothing
        about 8 kHz Indic accuracy. It occupies the ASR slot so the dialogue layer can be built
        and exercised. See apps/server.py.
"""

from __future__ import annotations

from typing import Iterator, Protocol, runtime_checkable


@runtime_checkable
class ASR(Protocol):
    """Streaming speech to text.

    Implementations MUST emit partial hypotheses during speech and a final one after
    end-of-turn. The latency the customer feels is the tail after they stop talking; anything
    that waits for the whole utterance before starting has already lost the budget
    (DESIGN 2.1 - ASR finalisation overlaps endpointing).
    """

    sample_rate: int          # 8000 in production. Anything else is a harness.
    india_resident: bool      # constraint 4. False disqualifies it from any runtime path.

    def stream(self, pcm: Iterator[bytes], locale: str) -> Iterator[tuple[str, bool]]:
        """Yield (text, is_final). Partials may be revised; the final one may not."""
        ...


@runtime_checkable
class TTS(Protocol):
    """Text to speech, used at build time rather than call time.

    ADR-005: every fixed approved line is rendered once, offline, per language, and cached. Only
    per-customer spans - offer amount, tenure - are synthesised live. At 20.4 lakh conversations
    a month the difference is paying to speak the same BLC-approved sentence two million times
    or paying to speak it once.
    """

    sample_rate: int
    india_resident: bool

    def render(self, text: str, locale: str) -> bytes:
        """Return PCM for one approved line. Called by the pre-render build step."""
        ...


class BrowserASR:
    """Placeholder occupying the ASR slot. The browser does the work; see apps/server.py.

    Present so the boundary is real rather than notional - if this class cannot satisfy the
    protocol, the protocol is wrong, and better to find that out now than when the real model
    arrives.
    """

    sample_rate = 16000
    india_resident = False

    def stream(self, pcm, locale):
        raise NotImplementedError(
            "speech is handled client-side by the Web Speech API; audio never reaches Python. "
            "This class marks the slot a real streaming ASR will occupy.")
