"""Load the approved-content set and index it for the runtime.

ADR-002: the runtime never composes customer-facing text. It resolves an identifier to an
approved string and plays that. Everything in this module is lookup; nothing generates.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
from dataclasses import dataclass, field

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_PACK = ROOT / "content"

SLOT = re.compile(r"\{([a-z_]+)\}")


class MissingSlot(KeyError):
    """A campaign variable the line needs was not supplied.

    This is fatal by design. Playing "your limit can go up to {enhanced_limit}" with the braces
    still in it, or silently dropping the amount, are both worse than not making the call.
    """


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    line: dict
    routes: dict = field(default_factory=dict)
    intent_set: tuple = ()
    requires_disclosure: tuple = ()
    plays_disclosure: tuple = ()
    never_say: tuple = ()
    variants: dict = field(default_factory=dict)   # locale -> [approved alternate phrasings]
    faq_scope: tuple = ()
    faq_enabled: bool = False
    next: str | None = None
    on_max_visits: str | None = None
    max_visits: int | None = None
    disposition: str | None = None
    escalate: bool = False


@dataclass(frozen=True)
class FaqEntry:
    id: str
    scope: str
    question: dict
    answer: dict
    paraphrases: dict = field(default_factory=dict)
    never_say: tuple = ()


@dataclass(frozen=True)
class Product:
    name: str
    entry: str
    nodes: dict
    global_routes: dict
    version: str


class Content:
    """Everything the bot is allowed to say, and the rules about when.

    A pack is a directory. The runtime has no other source of customer-facing language, so
    replacing the synthetic content with SBIC's BLC-approved script is `Content(path)` and
    nothing else. Nothing downstream - router, machine, session, telemetry, reports - knows or
    cares which pack is loaded.
    """

    def __init__(self, pack=None):
        self.root = pathlib.Path(pack) if pack else DEFAULT_PACK
        if not (self.root / "pack.yaml").exists():
            raise FileNotFoundError(f"{self.root} is not a content pack (no pack.yaml)")
        self.manifest = self._load("pack.yaml")
        self.pack_name = self.manifest["name"]
        self.pack_version = self.manifest["version"]
        self.provenance = self.manifest["provenance"]
        self.approval_ref = self.manifest.get("approval_ref")

        self.vars = self._load("campaign_vars.yaml")
        self.disclosures = self._load("disclosures.yaml")["disclosures"]
        self.intents = self._load("intents.yaml")["intents"]
        self.out_of_scope = self._load("out_of_scope.yaml")
        self.acceptance = self._load("acceptance.yaml")
        try:
            self.backchannels = self._load("backchannels.yaml")
        except FileNotFoundError:
            self.backchannels = {"tokens": {}, "play_probability": 0.0}
        self.locales = self.vars["required_locale"]
        self.bands = self.vars["confidence"]

        self.faq: dict[str, FaqEntry] = {}
        self.faq_by_scope: dict[str, list[str]] = {}
        for path in sorted((self.root / "faq").glob("*.yaml")):
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            scope = doc["scope"]
            self.faq_by_scope[scope] = []
            for e in doc["entries"]:
                entry = FaqEntry(
                    id=e["id"], scope=scope, question=e["question"], answer=e["answer"],
                    paraphrases={k.replace("paraphrases_", ""): v
                                 for k, v in e.items() if k.startswith("paraphrases_")},
                    never_say=tuple(e.get("never_say") or ()))
                self.faq[entry.id] = entry
                self.faq_by_scope[scope].append(entry.id)

        self.products: dict[str, Product] = {}
        for path in sorted((self.root / "script").glob("*.yaml")):
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            nodes = {}
            for n in doc["nodes"]:
                nodes[n["id"]] = Node(
                    id=n["id"], kind=n["kind"], line=n.get("line") or {},
                    routes=n.get("routes") or {},
                    intent_set=tuple(n.get("intent_set") or ()),
                    requires_disclosure=tuple(n.get("requires_disclosure") or ()),
                    plays_disclosure=tuple(n.get("plays_disclosure") or ()),
                    never_say=tuple(n.get("never_say") or ()),
                    variants=n.get("variants") or {},
                    faq_scope=tuple(n.get("faq_scope") or ()),
                    faq_enabled=bool(n.get("faq_enabled")),
                    next=n.get("next"), on_max_visits=n.get("on_max_visits"),
                    max_visits=n.get("max_visits"), disposition=n.get("disposition"),
                    escalate=bool(n.get("escalate")))
            self.products[doc["product"]] = Product(
                name=doc["product"], entry=doc["entry"], nodes=nodes,
                global_routes=doc.get("global_routes") or {}, version=doc["version"])

        self.global_intents = {k for k, v in self.intents.items() if v.get("global")}
        self.content_hash = self._hash()

    def _load(self, rel):
        return yaml.safe_load((self.root / rel).read_text(encoding="utf-8"))

    def _hash(self) -> str:
        """Fingerprint of every byte of the pack.

        Goes into every audit row. Constraint 5 - an audit trail that cannot say exactly which
        words were approved when the call happened is not an audit trail. A version string in a
        manifest is a claim; this is evidence, and it changes when someone edits a line and
        forgets to bump the version.
        """
        digest = hashlib.sha256()
        for path in sorted(self.root.rglob("*.yaml")):
            digest.update(path.relative_to(self.root).as_posix().encode())
            digest.update(path.read_bytes())
        return digest.hexdigest()[:16]

    def describe(self) -> dict:
        return {
            "pack": self.pack_name,
            "pack_version": self.pack_version,
            "provenance": self.provenance,
            "approval_ref": self.approval_ref,
            "content_hash": self.content_hash,
            "products": sorted(self.products),
            "locales": list(self.locales),
            "nodes": sum(len(p.nodes) for p in self.products.values()),
            "faq_entries": len(self.faq),
            "out_of_scope_categories": len(self.out_of_scope["categories"]),
        }

    # -- rendering -----------------------------------------------------------

    def render(self, text: str, campaign: dict) -> str:
        """Substitute campaign variables. Raises rather than guessing."""
        missing = [s for s in SLOT.findall(text) if s not in campaign]
        if missing:
            raise MissingSlot(f"campaign variables not supplied: {', '.join(missing)}")
        return SLOT.sub(lambda m: str(campaign[m.group(1)]), text)

    def node_template(self, product, node_id, locale, variant=0) -> str:
        """The approved template for this node, slots intact.

        `variants` holds additional BLC-approved phrasings of the SAME line. Rotating them is
        what stops a customer who is re-prompted twice hearing the identical sentence twice,
        which is the single most bot-like thing a voice agent does. Every variant is approved
        content - this is not paraphrasing, it is choosing between approved options.
        """
        node = self.products[product].nodes[node_id]
        options = [node.line.get(locale, "")] + list((node.variants or {}).get(locale, []))
        options = [o for o in options if o]
        return options[variant % len(options)] if options else ""

    def node_line(self, product, node_id, locale, campaign, variant=0):
        return self.render(self.node_template(product, node_id, locale, variant), campaign)

    def backchannel(self, category, locale, rng=None):
        """One approved acknowledgement token, or empty. Never generated."""
        import random
        rng = rng or random
        tokens = (self.backchannels.get("tokens") or {}).get(category, {}).get(locale) or []
        if not tokens or rng.random() > self.backchannels.get("play_probability", 0.0):
            return ""
        return rng.choice(tokens)

    def disclosure_line(self, did, locale, campaign):
        raw = " ".join(self.disclosures[did]["line"][locale].split())
        return self.render(raw, campaign)

    def faq_answer(self, fid, locale, campaign):
        return self.render(self.faq[fid].answer[locale], campaign)

    def example_campaign(self) -> dict:
        """Campaign variables built from the declared examples. Test data, not customer data."""
        return {k: v["example"] for k, v in self.vars["slots"].items() if "example" in v}
