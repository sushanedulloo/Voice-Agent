"""Feature 2 of the charter: sentiment and behavioural signals.

    "Analyze outbound call interactions to extract customer sentiment, trends, and
     behavioural insights"  - CH-S4 feature 2, FR-701

WHY THIS IS A LEXICON AND NOT A MODEL
-------------------------------------
Three reasons, in order of weight:

1. It runs INSIDE the turn loop. DESIGN 2.1 leaves ~50-100 ms for inline work (RESEARCH 2.5).
   A transformer classifier per turn, in nine languages, does not fit - and sentiment is not
   worth spending the barge-in budget on.
2. It must be explainable. "Why did this call get flagged as irritated?" has to be answerable
   with a list of matched tokens, not an embedding. A bank's QA team reviews these.
3. It has to work in nine languages on day one, with no labelled Indic call data. A lexicon we
   author is honest about being a heuristic; a model trained on English reviews and applied to
   Tamil telephony would be worse AND would look rigorous.

WHAT IT IS NOT
--------------
This is a SIGNAL, not a measurement. RESEARCH 2.6: in telecom transcripts humans flagged safety
issues 4-6x more often than LLM judges, and judge-human correlation is much weaker in telecom
than in retail. A lexicon is weaker still. So its output drives triage and trend reporting, and
is never the sole basis for a decision about a customer.

Calibration against human-labelled calls is required before any number from here is quoted
externally. Until then `calibrated = False` and the reports say so.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

CALIBRATED = False          # flips only after agreement is measured against human labels

MIN_TURNS_FOR_TREND = 4     # below this a call is too short to have a trajectory
ESCALATION_DROP = 0.5       # polarity fall, second half vs first, to call it escalating

# Behavioural signals, not just polarity. The charter asks for "behavioural insights", and
# "irritated" and "confused" need different handling from "negative".
LEXICON = {
    "positive": {
        "en": ["yes", "sure", "okay", "good", "great", "interested", "please", "thank",
               "alright", "fine", "go ahead", "sounds good", "helpful"],
        "hi": ["हाँ", "जी", "ठीक", "अच्छा", "बिल्कुल", "ज़रूर", "धन्यवाद", "सही", "बढ़िया"],
        "hi_latn": ["haan", "ji", "theek", "accha", "bilkul", "zaroor", "sahi", "badhiya"],
        "mr": ["हो", "बरं", "ठीक", "छान", "नक्की", "धन्यवाद", "चांगलं"],
        "gu": ["હા", "સારું", "ઠીક", "ચોક્કસ", "આભાર", "બરાબર"],
        "bn": ["হ্যাঁ", "আচ্ছা", "ঠিক", "ভালো", "অবশ্যই", "ধন্যবাদ"],
        "ta": ["ஆமா", "சரி", "நல்ல", "கண்டிப்பா", "நன்றி", "ஓகே"],
        "te": ["అవును", "సరే", "మంచి", "తప్పకుండా", "ధన్యవాదాలు", "ఓకే"],
        "kn": ["ಹೌದು", "ಸರಿ", "ಒಳ್ಳೆಯ", "ಖಂಡಿತ", "ಧನ್ಯವಾದ", "ಓಕೆ"],
        "ml": ["അതെ", "ശരി", "നല്ല", "തീർച്ചയായും", "നന്ദി", "ഓകെ"],
    },
    "negative": {
        "en": ["no", "not", "don't", "never", "wrong", "bad", "useless", "waste", "expensive",
               "costly", "problem", "refuse", "cancel"],
        "hi": ["नहीं", "मत", "गलत", "बेकार", "महंगा", "समस्या", "परेशानी", "नुकसान"],
        "hi_latn": ["nahi", "nahin", "mat", "galat", "bekar", "mehenga", "problem"],
        "mr": ["नाही", "नको", "चुकीचं", "बेकार", "महाग", "त्रास"],
        "gu": ["ના", "નથી", "ખોટું", "નકામું", "મોંઘું", "તકલીફ"],
        "bn": ["না", "নেই", "ভুল", "অকেজো", "দামি", "সমস্যা"],
        "ta": ["இல்ல", "வேணாம்", "தப்பு", "வேஸ்ட்", "காஸ்ட்லி", "பிரச்சனை"],
        "te": ["లేదు", "వద్దు", "తప్పు", "వేస్ట్", "ఖరీదు", "సమస్య"],
        "kn": ["ಇಲ್ಲ", "ಬೇಡ", "ತಪ್ಪು", "ವೇಸ್ಟ್", "ದುಬಾರಿ", "ಸಮಸ್ಯೆ"],
        "ml": ["ഇല്ല", "വേണ്ട", "തെറ്റ്", "വേസ്റ്റ്", "ചെലവ്", "പ്രശ്നം"],
    },
    # Annoyance. Distinct from negative: a customer can decline politely (negative, not
    # irritated) or agree while furious (positive polarity, irritated). They need different
    # advisor handling, so they are separate axes.
    "irritated": {
        "en": ["stop", "again", "already told", "how many times", "nuisance", "harassment",
               "fed up", "annoying", "busy", "leave me"],
        "hi": ["बंद", "बार बार", "पहले भी", "कितनी बार", "परेशान", "तंग", "छोड़ो"],
        "hi_latn": ["band karo", "baar baar", "pehle bhi", "pareshan", "tang", "chodo"],
        "mr": ["बंद", "पुन्हा पुन्हा", "त्रास", "सोडा"],
        "gu": ["બંધ", "વારંવાર", "પરેશાન", "છોડો"],
        "bn": ["বন্ধ", "বারবার", "বিরক্ত", "ছাড়ুন"],
        "ta": ["நிறுத்து", "திரும்ப திரும்ப", "தொந்தரவு", "விடுங்க"],
        "te": ["ఆపండి", "మళ్ళీ మళ్ళీ", "విసుగు", "వదిలేయండి"],
        "kn": ["ನಿಲ್ಲಿಸಿ", "ಮತ್ತೆ ಮತ್ತೆ", "ಕಿರಿಕಿರಿ", "ಬಿಡಿ"],
        "ml": ["നിർത്തൂ", "വീണ്ടും വീണ്ടും", "ശല്യം", "വിടൂ"],
    },
    # Did not understand. Drives a re-prompt or a human, not a sales push.
    "confused": {
        # NOT bare interrogatives. "what"/"क्या"/"என்ன"/"શું" appear in almost every question a
        # customer asks, so including them labelled every engaged question as confusion - the
        # opposite reading, on the turns that matter most.
        "en": ["sorry", "repeat", "understand", "meaning", "explain", "confused",
               "didn't get", "come again", "say that again", "what do you mean"],
        "hi": ["समझ", "दोबारा", "फिर से", "मतलब", "समझा", "समझ नहीं"],
        "hi_latn": ["kya", "samajh", "dobara", "phir se", "matlab"],
        "mr": ["समजलं", "समजलं नाही", "पुन्हा", "अर्थ"],
        "gu": ["સમજ", "સમજાયું નહીં", "ફરીથી", "અર્થ"],
        "bn": ["বুঝ", "বুঝিনি", "আবার", "মানে"],
        "ta": ["புரிய", "புரியல", "மறுபடியும்", "அர்த்தம்"],
        "te": ["అర్థం", "అర్థం కాలేదు", "మళ్ళీ"],
        "kn": ["ಅರ್ಥ", "ಅರ್ಥ ಆಗಲಿಲ್ಲ", "ಮತ್ತೆ"],
        "ml": ["മനസ്സില", "മനസ്സിലായില്ല", "വീണ്ടും", "അർത്ഥം"],
    },
    # Buying signals. The charter's "behavioural insights" - these are what a human agent hears
    # and a disposition code throws away.
    "engaged": {
        "en": ["how much", "when", "how many", "can i", "what if", "tell me", "more",
               "details", "explain"],
        "hi": ["कितना", "कब", "कैसे", "बताइए", "ज़्यादा", "डिटेल"],
        "hi_latn": ["kitna", "kab", "kaise", "bataiye", "zyada", "detail"],
        "mr": ["किती", "कधी", "कसं", "सांगा", "डिटेल"],
        "gu": ["કેટલું", "ક્યારે", "કેવી રીતે", "કહો", "વિગત"],
        "bn": ["কত", "কখন", "কীভাবে", "বলুন", "বিস্তারিত"],
        "ta": ["எவ்வளவு", "எப்போது", "எப்படி", "சொல்லுங்க", "விவரம்"],
        "te": ["ఎంత", "ఎప్పుడు", "ఎలా", "చెప్పండి", "వివరాలు"],
        "kn": ["ಎಷ್ಟು", "ಯಾವಾಗ", "ಹೇಗೆ", "ಹೇಳಿ", "ವಿವರ"],
        "ml": ["എത്ര", "എപ്പോൾ", "എങ്ങനെ", "പറയൂ", "വിവരം"],
    },
}

AXES = tuple(LEXICON)
_WORD = re.compile(r"[\wऀ-෿]+", re.UNICODE)


# Single tokens too weak to carry sentiment alone. Without this, "leave me" contributes "me" to
# the irritated axis and "yes tell me more" scores as irritated - not a tuning problem, the
# opposite answer.
STOP = {"me", "my", "i", "you", "to", "a", "is", "it", "the", "and", "so", "of", "for"}


def _index():
    """Two matchers.

    UNIGRAM  single-word terms, matched per token
    PHRASE   multi-word terms, matched as a substring and consuming their words

    Splitting "leave me" or "already told" into words was the original bug: the fragments are
    meaningless alone and fire on ordinary sentences.
    """
    unigram: dict[str, set] = {}
    phrase: list = []
    for axis, langs in LEXICON.items():
        for terms in langs.values():
            for term in terms:
                toks = _WORD.findall(term.lower())
                if len(toks) > 1:
                    phrase.append((term.lower(), axis))
                elif toks and toks[0] not in STOP:
                    unigram.setdefault(toks[0], set()).add(axis)
    return unigram, sorted(phrase, key=lambda p: -len(p[0]))


UNIGRAM, PHRASES = _index()

# A token in several axes ("again" is confused AND irritated) counts at half weight, so one
# shared word cannot outvote an unambiguous signal elsewhere in the utterance.
AMBIGUOUS_WEIGHT = 0.5


@dataclass
class TurnSentiment:
    polarity: float                 # -1..+1
    axes: dict = field(default_factory=dict)
    matched: list = field(default_factory=list)   # the tokens that fired - explainability

    @property
    def label(self) -> str:
        if self.axes.get("irritated"):
            return "irritated"
        if self.axes.get("confused"):
            return "confused"
        if self.polarity > 0.2:
            return "positive"
        if self.polarity < -0.2:
            return "negative"
        return "neutral"


def score_turn(text: str) -> TurnSentiment:
    """One utterance. O(tokens), no model, no network."""
    counts, matched = Counter(), []

    # Phrases first. They are the strong signal, and they consume their own words so the
    # fragments ("me" from "leave me") cannot fire again as loose tokens.
    consumed = (text or "").lower()
    for term, axis in PHRASES:
        if term in consumed:
            counts[axis] += 2
            matched.append((term, axis))
            consumed = consumed.replace(term, " ")

    for tok in _WORD.findall(consumed):
        axes = UNIGRAM.get(tok)
        if not axes:
            continue
        weight = 1.0 if len(axes) == 1 else AMBIGUOUS_WEIGHT
        for axis in axes:
            counts[axis] += weight
            matched.append((tok, axis))
    pos, neg = counts["positive"], counts["negative"] + counts["irritated"]
    total = pos + neg
    polarity = (pos - neg) / total if total else 0.0
    return TurnSentiment(round(polarity, 3), dict(counts), matched[:8])


@dataclass
class CallSentiment:
    overall: float
    label: str
    trajectory: list                # per-turn polarity, in order
    axes: dict
    turns: int
    escalating: bool                # got worse as the call went on

    def to_dict(self) -> dict:
        return {"overall": self.overall, "label": self.label, "axes": self.axes,
                "trajectory": self.trajectory, "turns": self.turns,
                "escalating": self.escalating, "calibrated": CALIBRATED}


def score_call(utterances: list) -> CallSentiment:
    """Aggregate a call. Later turns weigh more - how a call ENDS predicts the outcome better
    than how it opens, and an advisor picking up a transfer needs the current mood, not the
    average one."""
    scored = [score_turn(t) for t in utterances if (t or "").strip()]
    if not scored:
        return CallSentiment(0.0, "neutral", [], {}, 0, False)

    weights = [1.0 + i * 0.5 for i in range(len(scored))]
    overall = sum(s.polarity * w for s, w in zip(scored, weights)) / sum(weights)

    axes = Counter()
    for s in scored:
        axes.update(s.axes)

    # A trend needs enough turns to be a trend. Below MIN_TURNS_FOR_TREND the halves are one
    # turn each and every dip looks like escalation - which flagged 72% of calls and made the
    # signal worthless. Explicit irritation still counts at any length, because that is an
    # observation rather than a trend.
    escalating = axes.get("irritated", 0) >= 2
    if len(scored) >= MIN_TURNS_FOR_TREND:
        half = len(scored) // 2
        first = sum(s.polarity for s in scored[:half]) / half
        last = sum(s.polarity for s in scored[-half:]) / half
        escalating = escalating or (last < first - ESCALATION_DROP and last < 0)

    # Confused outranks irritated. "Say that again" is a re-prompt, not anger, and handing a
    # confused customer to an escalation path is the more expensive of the two mistakes.
    if axes.get("confused", 0) > axes.get("irritated", 0):
        label = "confused"
    elif axes.get("irritated", 0) >= 1:
        label = "irritated"
    elif overall > 0.2:
        label = "positive"
    elif overall < -0.2:
        label = "negative"
    else:
        label = "neutral"

    return CallSentiment(round(overall, 3), label,
                         [s.polarity for s in scored], dict(axes),
                         len(scored), escalating)
