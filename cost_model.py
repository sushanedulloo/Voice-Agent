"""
SBI Card outbound voice AI - bottom-up cost model.

Every number that is OURS (not SBI Card's) is a constant below with a source
comment. Replace them with client actuals as they arrive; everything downstream
recomputes. Run: python cost_model.py

Researched Sept 2026. Sources in SOURCES at the bottom.
"""

# ---------------------------------------------------------------- FX
USD_INR = 95.7                  # market mid, 14 Sep 2026

# ------------------------------------------------- volume & call shape
# Derived from SBI Card's own charter: unfyd quoted Rs 2.76 Cr/mo at Rs 9/min.
BILLED_MIN_AT_UNFYD   = 2_76_00_000 / 9          # 30.67 lakh minutes/month
HUMAN_PITCH_SEC       = 90                       # est; measure from their recordings
CONVERSATIONS_PER_MO  = BILLED_MIN_AT_UNFYD / (HUMAN_PITCH_SEC / 60)   # 20.4 lakh

BOT_TALK_SEC          = 50      # our design target (the "fifty-second rule")
BOT_SPEAK_SHARE       = 0.45    # share of call the bot is the one speaking
CHARS_PER_SEC         = 13.5    # ~150 wpm x ~5.5 chars/word, Hindi/Indian English
TURNS_PER_CALL        = 7

# calling window -> concurrency
CALL_DAYS_PER_MO      = 26
CALL_HOURS_PER_DAY    = 9       # TCCCPR-permissible window actually worked
PEAK_FACTOR           = 2.0

# ------------------------------------------------------ vendor rates
# Sarvam AI published list, Sept 2026 (India-hosted, sovereign - satisfies RBI)
SARVAM_STT_PER_HR     = 30.0    # Saarika
SARVAM_TTS_PER_10K    = 30.0    # Bulbul v3 (doubled from v2's Rs 15 in Aug 2026)
SARVAM_LLM_CACHED_MTK = 10.98   # Sarvam 105B cached input
SARVAM_LLM_OUT_MTK    = 73.20   # Sarvam 105B output
FLASH_LLM_CACHED_MTK  = 0.63    # DeepSeek V4 Flash cached input (cheapest on Sarvam)
FLASH_LLM_OUT_MTK     = 59.40

# GPU, Indian providers
L40S_PER_HR           = 102.0   # E2E Networks on-demand
# WARNING: streams-per-GPU assumes NVIDIA MPS + TensorRT are actually implemented.
# A single ASR request uses only 15-20% of an L40S's SMs by default; naive serving
# lands 4x worse (one documented deployment: 16 GPUs -> 4 with MPS, -> 2 adding
# TensorRT). That 4x is engineering effort, not a procurement choice. If the MPS
# work is not funded, halve both numbers below. See docs/DESIGN.md section 4.
STT_STREAMS_PER_L40S  = 50      # 8 kHz streaming ASR, MPS-enabled
LLM_STREAMS_PER_L40S  = 80      # quantised ~8B, short prompts, MPS-enabled

# prompt shape per turn
# Deliberately conservative. ADR-004 routes most turns through an embedding
# cascade (16-100 ms, ~65x cheaper than LLM classification), escalating to a
# model only on low confidence. Costing every turn as a full LLM call puts the
# error on the safe side of the quote.
CACHED_PROMPT_TOKENS  = 1500    # frozen script node + FAQ grounding, cache-hit
OUTPUT_TOKENS         = 60      # one short line or one intent label

# --------------------------------------------------- script pre-render
# Most turns play a BLC-approved fixed line. Record those ONCE per language;
# only variable spans (amount, tenure, name) need runtime TTS.
PRERENDERED_SHARE     = 0.80

# ------------------------------------------------------- fixed cost
# Rs/month. Our estimate - finance must cost the run team before any quote.
RUN_TEAM_PER_MO       = 15_80_000   # 6 eng + 3 QA + 1 ops lead + 0.5 DS, 1.35x loaded
BUILD_AMORT_PER_MO    = 8_33_000    # Rs 2 Cr build over 24 months
PLATFORM_INFRA_PER_MO = 4_00_000    # monitoring, staging, DR, security tooling, archive
COMPLIANCE_PER_MO     = 1_50_000    # SOC2/ISO/pentest amortised
FIXED_PER_MO          = (RUN_TEAM_PER_MO + BUILD_AMORT_PER_MO
                         + PLATFORM_INFRA_PER_MO + COMPLIANCE_PER_MO)

# ------------------------------------------------------ human baseline
SEAT_COST_LOW         = 28_000   # tier-2 fully loaded (Context.md assumption)
SEAT_COST_HIGH        = 38_500   # tier-1 fully loaded (2026 benchmark)
SHIFT_HOURS           = 8
TALK_UTILISATION      = 0.35

# ---------------------------------------------------------- funnel
AGREE_RATE_HUMAN      = 0.12
AGREE_RATE_BOT        = 0.11    # 92% of human; measure against control arm
CONSENT_TO_BOOKING    = 0.70

# ---------------------------------------------------------- pricing
TARGET_MARGIN         = 0.30


# ============================================================ helpers
def lakh(x):
    return x / 1_00_000


def crore(x):
    return x / 1_00_00_000


def concurrency():
    """Average and peak simultaneous bot legs at Phase-1 coverage."""
    bot_minutes = CONVERSATIONS_PER_MO * BOT_TALK_SEC / 60
    window_min = CALL_DAYS_PER_MO * CALL_HOURS_PER_DAY * 60
    avg = bot_minutes / window_min
    return avg, avg * PEAK_FACTOR


def gpu_cost_per_conversation(streams_per_gpu, always_on):
    """Rs/conversation for a self-hosted GPU tier sized to peak concurrency."""
    _, peak = concurrency()
    gpus = -(-peak // streams_per_gpu)           # ceil
    hours = 730 if always_on else CALL_DAYS_PER_MO * CALL_HOURS_PER_DAY
    return gpus * hours * L40S_PER_HR / CONVERSATIONS_PER_MO, int(gpus)


def direct_cost(config):
    """Rs per contacted conversation, itemised. config: 'poc' | 'scale'."""
    call_min = BOT_TALK_SEC / 60
    spoken_chr = BOT_TALK_SEC * BOT_SPEAK_SHARE * CHARS_PER_SEC
    tts_chr = spoken_chr * (1 - PRERENDERED_SHARE)
    cached_tok = TURNS_PER_CALL * CACHED_PROMPT_TOKENS
    out_tok = TURNS_PER_CALL * OUTPUT_TOKENS

    if config == "poc":
        # managed APIs: no GPU ops, no capex, ships in weeks
        stt = SARVAM_STT_PER_HR / 60 * call_min
        tts = tts_chr / 10_000 * SARVAM_TTS_PER_10K
        llm = (cached_tok * SARVAM_LLM_CACHED_MTK
               + out_tok * SARVAM_LLM_OUT_MTK) / 1_000_000
        media = 0.05
    else:
        # self-hosted on Indian GPU, autoscaled to the calling window
        stt, _ = gpu_cost_per_conversation(STT_STREAMS_PER_L40S, always_on=False)
        tts = tts_chr / 10_000 * SARVAM_TTS_PER_10K * 0.25   # own Indic TTS weights
        llm, _ = gpu_cost_per_conversation(LLM_STREAMS_PER_L40S, always_on=False)
        media = 0.05

    return {
        "Speech to text": stt,
        "Text to speech": tts,
        "Reasoning model": llm,
        "Media + orchestration": media,
        "Recording + archive": 0.02,   # 3-yr Opus @ 8 kHz, India object storage
        "Telephony": 0.00,             # partner's SIP trunk
    }


def loaded_cost(config, conversations_per_mo):
    d = sum(direct_cost(config).values())
    return d + FIXED_PER_MO / conversations_per_mo, d


def human_cost_per_minute(seat):
    return seat / (CALL_DAYS_PER_MO * SHIFT_HOURS * 60 * TALK_UTILISATION)


def cost_per_agreement(cost_per_contact, agree_rate):
    return cost_per_contact / agree_rate


def cost_per_booking(cost_per_contact, agree_rate):
    return cost_per_contact / (agree_rate * CONSENT_TO_BOOKING)


# ============================================================== report
def main():
    avg, peak = concurrency()
    print("=" * 74)
    print("SBI CARD OUTBOUND VOICE AI - COST MODEL".center(74))
    print("(USD/INR 95.7 | Sarvam list | E2E GPU | Sept 2026)".center(74))
    print("=" * 74)

    print("\nPhase-1 coverage      %8.1f lakh conversations/month"
          % lakh(CONVERSATIONS_PER_MO))
    print("Billed if 90s (human) %8.1f lakh minutes" % lakh(BILLED_MIN_AT_UNFYD))
    print("Billed if %ds (bot)   %8.1f lakh minutes"
          % (BOT_TALK_SEC, lakh(CONVERSATIONS_PER_MO * BOT_TALK_SEC / 60)))
    print("Concurrency needed    %8.0f average, %.0f peak bot legs" % (avg, peak))

    for cfg, label in (("poc", "CONFIG A - managed APIs (POC, weeks 1-12)"),
                       ("scale", "CONFIG B - self-hosted India GPU (production)")):
        print("\n%s\n%s\n%s" % ("-" * 74, label, "-" * 74))
        items = direct_cost(cfg)
        for k, v in items.items():
            print("  %-24s Rs %6.3f /conversation" % (k, v))
        d = sum(items.values())
        print("  %-24s Rs %6.3f /conversation   (Rs %.2f/min-equivalent)"
              % ("DIRECT COST", d, d / (BOT_TALK_SEC / 60)))

    print("\n%s\nFIXED COST BASE (our estimate - finance must cost this)\n%s"
          % ("-" * 74, "-" * 74))
    for k, v in (("Run team", RUN_TEAM_PER_MO),
                 ("Build amortisation", BUILD_AMORT_PER_MO),
                 ("Platform infra", PLATFORM_INFRA_PER_MO),
                 ("Compliance", COMPLIANCE_PER_MO)):
        print("  %-24s Rs %6.2f lakh/month" % (k, lakh(v)))
    print("  %-24s Rs %6.2f lakh/month" % ("TOTAL FIXED", lakh(FIXED_PER_MO)))

    print("\n%s\nFULLY LOADED COST vs VOLUME  (fixed cost is the whole story)\n%s"
          % ("-" * 74, "-" * 74))
    print("  %-22s%14s%14s%16s" % ("Conversations/mo", "Config A", "Config B", "Fixed share"))
    for v in (3_00_000, 5_00_000, 10_00_000, int(CONVERSATIONS_PER_MO), 40_00_000):
        a, _ = loaded_cost("poc", v)
        b, _ = loaded_cost("scale", v)
        print("  %6.1f lakh%12sRs %8.2f  Rs %8.2f   Rs %6.2f/conv"
              % (lakh(v), "", a, b, FIXED_PER_MO / v))

    print("\n%s\nTHE HUMAN WE ARE REPLACING (the number that decides the deal)\n%s"
          % ("-" * 74, "-" * 74))
    for seat in (SEAT_COST_LOW, SEAT_COST_HIGH):
        cpm = human_cost_per_minute(seat)
        pitch = cpm * HUMAN_PITCH_SEC / 60
        print("  Seat Rs %s/mo @ %.0f%% utilisation -> Rs %.2f/talk-minute, "
              "Rs %.2f per %ds pitch"
              % (format(seat, ","), TALK_UTILISATION * 100, cpm, pitch, HUMAN_PITCH_SEC))
        print("      cost per agreement Rs %.2f | per booked SR Rs %.2f"
              % (cost_per_agreement(pitch, AGREE_RATE_HUMAN),
                 cost_per_booking(pitch, AGREE_RATE_HUMAN)))

    print("\n%s\nPRICE FLOOR AND RECOMMENDED QUOTE\n%s" % ("-" * 74, "-" * 74))
    loaded_a, _ = loaded_cost("poc", CONVERSATIONS_PER_MO)
    loaded_b, _ = loaded_cost("scale", CONVERSATIONS_PER_MO)
    for name, c in (("Config A (POC stack)", loaded_a),
                    ("Config B (production)", loaded_b)):
        floor = c / (1 - TARGET_MARGIN)
        print("  %-22s cost Rs %.2f  ->  Rs %.2f/conversation at %.0f%% margin "
              "(Rs %.2f/min-equiv)"
              % (name, c, floor, TARGET_MARGIN * 100, floor / (BOT_TALK_SEC / 60)))

    print("\n%s\nWHAT IT COSTS SBI CARD, PER OUTCOME\n%s" % ("-" * 74, "-" * 74))
    quote = 4.75
    print("  At our Rs %.2f/conversation floor, bot agreement %.0f%%:"
          % (quote, AGREE_RATE_BOT * 100))
    print("      cost per agreement  Rs %6.2f" % cost_per_agreement(quote, AGREE_RATE_BOT))
    print("      cost per booked SR  Rs %6.2f" % cost_per_booking(quote, AGREE_RATE_BOT))
    for seat in (SEAT_COST_LOW, SEAT_COST_HIGH):
        pitch = human_cost_per_minute(seat) * HUMAN_PITCH_SEC / 60
        hb = cost_per_booking(pitch, AGREE_RATE_HUMAN)
        bb = cost_per_booking(quote, AGREE_RATE_BOT)
        print("      vs human @ Rs %s seat: Rs %6.2f  ->  %+.0f%% cost per booked SR"
              % (format(seat, ","), hb, (bb - hb) / hb * 100))

    print("\n  Monthly bill at Phase-1 coverage:")
    for label, rate in (("unfyd.AI  Rs 9.00/min x 90s", 9.0 * 1.5),
                        ("TransOrg  Rs 4.75/conversation", 4.75),
                        ("TransOrg  Rs 5.77 blended", 5.77),
                        ("TransOrg  Rs 6.50 cap", 6.50)):
        m = rate * CONVERSATIONS_PER_MO
        print("      %-34s Rs %5.2f Cr/mo   Rs %6.2f Cr/yr"
              % (label, crore(m), crore(m * 12)))
    print("=" * 74)


def demo():
    """Self-check: the arithmetic the quote rests on."""
    avg, peak = concurrency()
    assert 100 < avg < 150, avg                      # ~122 concurrent, not 1000
    assert peak == avg * PEAK_FACTOR

    a = sum(direct_cost("poc").values())
    b = sum(direct_cost("scale").values())
    assert b < a, "self-hosting must beat managed APIs at scale"
    assert 0.4 < a < 1.2 and 0.1 < b < 0.6, (a, b)

    # fixed cost dominates at low volume - this is why the POC loses money
    small, _ = loaded_cost("scale", 3_00_000)
    big, _ = loaded_cost("scale", CONVERSATIONS_PER_MO)
    assert small > 5 * big, (small, big)

    # the central claim: at Rs 4.75 we must beat the human per booked SR
    pitch = human_cost_per_minute(SEAT_COST_LOW) * HUMAN_PITCH_SEC / 60
    assert round(pitch, 2) == 9.62, pitch            # Rs 6.41/min x 1.5 min
    assert cost_per_booking(4.75, AGREE_RATE_BOT) < cost_per_booking(pitch, AGREE_RATE_HUMAN)

    # the fifty-second rule: beyond this the bot costs more than the advisor
    breakeven = pitch / 9.0 * 60
    assert 63 < breakeven < 65, breakeven            # 64 s at Rs 9/min

    # margin sanity
    loaded, _ = loaded_cost("scale", CONVERSATIONS_PER_MO)
    assert loaded < 4.75, "Rs 4.75 floor must clear fully loaded cost"
    print("demo: ok")


SOURCES = """
Sarvam AI pricing      https://docs.sarvam.ai/api-reference-docs/pricing
E2E Networks GPU       https://www.e2enetworks.com/blog/nvidia-a100-price-india
India voice AI rates   https://caller.digital/voice-ai-pricing-india
Vendor teardown        https://caller.digital/blog/voice-ai-vendor-pricing-teardown-india-2026
Human vs AI cost       https://www.caller.digital/blog/ai-voice-agent-vs-human-india-cost-roi
Deepgram (USD bench)   https://convertaudiototext.com/blog/deepgram-nova-3-explained
Self-host break-even   https://www.spheron.network/blog/faster-whisper-gpu-cloud-production-deployment-guide/
Seat cost benchmark    https://www.1840andco.com/blog/call-center-outsourcing-in-india
SIP trunk India        https://www.plivo.com/sip-trunking/pricing/in/
"""

if __name__ == "__main__":
    demo()
    main()
