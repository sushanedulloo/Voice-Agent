"""Closed-set router: utterance in, identifier out.

ADR-002 fixed the output - an id from the approved set, or OUT_OF_SCOPE. This module decides
which id. ADR-004 specifies the production design: embedding retrieval on the hot path,
escalating to a constrained LLM router only on low-confidence turns.

WHAT THIS IS: a TF-IDF character-ngram stand-in for that embedding retrieval, so the rest of
the system can be built, exercised and measured before any component decision is made. It is
the right shape and the wrong model. Character ngrams are used deliberately - they tolerate the
spelling variation in romanised Hindi far better than word tokens.

WHAT IT IS NOT: calibrated. RESEARCH 2.4 requires per-class rejection thresholds tuned per
language against real traffic. The thresholds below are dev values picked to make the harness
behave; they are not evidence and must not be quoted.

What IS faithful here, and is the part that matters:

  - OUT_OF_SCOPE is a trained class with its own examples competing directly against every
    in-scope candidate, not the residue of a threshold. If an off-glossary example scores higher
    than the best approved candidate, we deflect regardless of the band.
  - Scores are independent per candidate (cosine against that candidate's own examples), never
    normalised across candidates. Softmax would force probability mass onto some class by
    construction and could not express "none of these" - and a confident misroute on a credit
    product is mis-selling.
  - The candidate set is restricted to the current node's permitted intents plus the FAQ in
    scope. A question about EMI tenure cannot be answered at the opening node, because that
    candidate is not in the set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion

# Dev thresholds for the TF-IDF stand-in. NOT the production bands in campaign_vars.yaml,
# which belong to the calibrated embedding router. See module docstring.
DEV_AUTO = 0.45
DEV_FLAG = 0.22


@dataclass
class Route:
    kind: str                 # "intent" | "faq" | "out_of_scope"
    id: str
    confidence: float
    band: str                 # "auto" | "flag" | "deflect"
    alternatives: list = field(default_factory=list)

    @property
    def actionable(self) -> bool:
        return self.band in ("auto", "flag") and self.kind != "out_of_scope"


class Router:
    def __init__(self, content, locale="en"):
        self.content = content
        self.locale = locale
        self._texts: list[str] = []
        self._owner: list[tuple] = []          # (kind, id) per text

        # Index EVERY language the content declares an example in - NOT just the locales we can
        # speak. Those are different sets and conflating them is a real bug:
        #
        #   what we SPEAK  (content.locales)  drives TTS and the approved line we play
        #   what we HEAR   (every examples_*) drives matching against ASR output
        #
        # indic-conformer emits native script, so Devanagari anchors must be indexed even though
        # the spoken locale is hi_latn (romanised, which is what the TTS voice takes). Indexing
        # only content.locales scored real Hindi ASR output at 0.000 and deflected every turn.
        #
        # Indexing all of them together is also right for code-mixing: a Hindi call routinely
        # contains "EMI" and "processing fee" in English, and an English call contains "haan".
        langs = set(content.locales)
        for spec in content.intents.values():
            langs |= {k.replace("examples_", "") for k in spec if k.startswith("examples_")}
        for cat in content.out_of_scope["categories"]:
            langs |= {k.replace("examples_", "") for k in cat if k.startswith("examples_")}
        for entry in content.faq.values():
            langs |= set(entry.question) | set(entry.paraphrases)
        for lang in sorted(langs):
            for name, spec in content.intents.items():
                for ex in spec.get(f"examples_{lang}") or []:
                    self._add(ex, ("intent", name))
            for fid, entry in content.faq.items():
                if lang in entry.question:
                    self._add(entry.question[lang], ("faq", fid))
                for ex in entry.paraphrases.get(lang) or []:
                    self._add(ex, ("faq", fid))
            for cat in content.out_of_scope["categories"]:
                for ex in cat.get(f"examples_{lang}") or []:
                    self._add(ex, ("out_of_scope", cat["id"]))

        # Char ngrams alone matched on function words - "yes that is me" scored against
        # "say that again" on the shared "that". On utterances this short, common substrings
        # dominate. Word features carry the content; char features keep the tolerance for
        # romanised-Hindi spelling drift ("nahi"/"nahin"/"nhi"). Both, unioned.
        self._vec = FeatureUnion([
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)),
        ])
        self._matrix = normalize(self._vec.fit_transform(self._texts))

    def _add(self, text, owner):
        if text and text.strip():
            self._texts.append(text.strip().lower())
            self._owner.append(owner)

    def candidates_at(self, product: str, node) -> set:
        """The only things the router may return at this node."""
        allowed = {("intent", i) for i in node.intent_set}
        allowed |= {("intent", i) for i in self.content.global_intents}
        if node.faq_enabled:
            for scope in node.faq_scope:
                allowed |= {("faq", f) for f in self.content.faq_by_scope.get(scope, [])}
        return allowed

    def route(self, utterance: str, product: str, node) -> Route:
        allowed = self.candidates_at(product, node)
        query = normalize(self._vec.transform([utterance.strip().lower()]))
        sims = (self._matrix @ query.T).toarray().ravel()

        best: dict[tuple, float] = {}
        for score, owner in zip(sims, self._owner):
            # OUT_OF_SCOPE examples always compete - that is what makes it a class and not a
            # leftover. Everything else must be permitted at this node.
            if owner[0] == "out_of_scope" or owner in allowed:
                if score > best.get(owner, -1.0):
                    best[owner] = float(score)

        if not best:
            return Route("out_of_scope", "OOS_NONSENSE", 0.0, "deflect")

        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
        (kind, ident), score = ranked[0]

        if score >= DEV_AUTO:
            band = "auto"
        elif score >= DEV_FLAG:
            band = "flag"
        else:
            band = "deflect"

        # Nothing cleared the floor: deflect rather than act on the nearest thing we found.
        if band == "deflect" and kind != "out_of_scope":
            return Route("out_of_scope", "OOS_NONSENSE", score, "deflect",
                         [(k, i, round(s, 3)) for (k, i), s in ranked[:4]])

        return Route(kind, ident, round(score, 4), band,
                     [(k, i, round(s, 3)) for (k, i), s in ranked[:4]])
