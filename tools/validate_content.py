#!/usr/bin/env python3
"""Validate the approved-content set, and render the human-readable view.

    python tools/validate_content.py            # validate, exit 1 on any error
    python tools/validate_content.py --render   # also write docs/SCRIPT.md

Why this exists: under ADR-002 the YAML in content/ IS the runtime artefact - the router
returns an identifier and the runtime plays the string these files hold. A dangling transition
is not a typo, it is a call that dead-airs in production. A pitch node reachable without its
disclosure is not untidy, it is an undisclosed offer on a recorded line at a bank.

Checks, in the order they run:

  C1  every transition target resolves to a node in the same product
  C2  every `normal` node can route OUT_OF_SCOPE, and that route ends at an approved line
      plus a human - there is no syntax for a generative fallback
  C3  every {slot} used is declared in campaign_vars.yaml
  C4  every node is reachable from `entry`, and every path terminates
  C5  a node carrying `requires_disclosure` cannot be reached on ANY path without those
      disclosures having played  (a must-analysis, not a spot check)
  C6  every node and FAQ answer has a line in every required locale
  C7  FAQ ids are globally unique
  C8  intent_set members exist in intents.yaml; `on` keys are covered by intent_set or globals
  C9  no `never_say` phrase appears in the content of the node that forbids it
  C10 no literal digit appears outside a {slot} - constraint 1, amounts are read, never written

Stdlib plus PyYAML, which is already installed. No test framework.
"""

import sys
import re
import pathlib
from collections import defaultdict

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"          # overridden by --pack

SLOT = re.compile(r"\{([a-z_]+)\}")
DIGIT_OUTSIDE_SLOT = re.compile(r"(?<!\{)\b\d+\b(?!\})")
# Nodes that wait for a customer turn. Only these can receive a globally-routed intent.
LISTENING = {"normal"}
DYNAMIC = {"__REPLAY__", "__RESUME__"}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, check, where, msg):
        self.errors.append((check, where, msg))

    def warn(self, check, where, msg):
        self.warnings.append((check, where, msg))


def load(path):
    with open(CONTENT / path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def successors(node, global_targets):
    """Every node this node can hand control to."""
    out = []
    if node.get("next"):
        out.append(node["next"])
    for target in (node.get("routes") or {}).values():
        if target not in DYNAMIC:
            out.append(target)
    if node.get("on_max_visits"):
        out.append(node["on_max_visits"])
    # A global intent can only be spoken at a node that is listening for one.
    if node["kind"] in LISTENING:
        out.extend(global_targets)
    return out


def check_product(product, vars_doc, intents_doc, faq_ids_by_scope, report):
    doc = load(f"script/{product}.yaml")
    nodes = {n["id"]: n for n in doc["nodes"]}
    where = f"script/{product}.yaml"
    declared_slots = set(vars_doc["slots"])
    locales = vars_doc["required_locale"]
    global_routes = doc.get("global_routes") or {}
    global_targets = [t for t in global_routes.values() if t not in DYNAMIC]

    if len(nodes) != len(doc["nodes"]):
        report.error("C1", where, "duplicate node id")

    # ---- C1 transitions resolve -------------------------------------------
    for nid, node in nodes.items():
        for target in successors(node, []):
            if target not in nodes:
                report.error("C1", f"{where}:{nid}", f"transition to unknown node {target!r}")
    for intent, target in global_routes.items():
        if target not in DYNAMIC and target not in nodes:
            report.error("C1", where, f"global_routes[{intent}] -> unknown node {target!r}")

    # ---- C2 out-of-scope always has an approved exit -----------------------
    oos = global_routes.get("OUT_OF_SCOPE")
    if not oos:
        report.error("C2", where, "no OUT_OF_SCOPE route defined")
    elif oos in nodes:
        # follow the deflection to its terminal and insist it reaches a human
        seen, cur, lands_on_human = set(), oos, False
        while cur in nodes and cur not in seen:
            seen.add(cur)
            if nodes[cur]["kind"] == "transfer":
                lands_on_human = True
                break
            cur = nodes[cur].get("next")
        if not lands_on_human:
            report.error("C2", f"{where}:{oos}",
                         "OUT_OF_SCOPE deflection does not end at a transfer to a human")
        if not nodes[oos].get("line", {}).get(locales[0]):
            report.error("C2", f"{where}:{oos}", "deflection node has no approved line")

    # ---- C3/C6/C9/C10 line-level checks ------------------------------------
    for nid, node in nodes.items():
        line = node.get("line") or {}
        for loc in locales:
            if loc not in line:
                report.error("C6", f"{where}:{nid}", f"missing locale {loc!r}")
        for loc, text in line.items():
            if not text:
                continue
            for slot in SLOT.findall(text):
                if slot not in declared_slots:
                    report.error("C3", f"{where}:{nid}:{loc}", f"undeclared slot {{{slot}}}")
            if DIGIT_OUTSIDE_SLOT.search(text):
                report.error("C10", f"{where}:{nid}:{loc}",
                             "literal number in an approved line - amounts must be slots")
            for phrase in node.get("never_say") or []:
                if phrase.lower() in text.lower():
                    report.error("C9", f"{where}:{nid}:{loc}",
                                 f"line contains its own never_say phrase {phrase!r}")

    # ---- C8 intents --------------------------------------------------------
    known_intents = set(intents_doc["intents"])
    globals_ = {k for k, v in intents_doc["intents"].items() if v.get("global")}
    for nid, node in nodes.items():
        declared = set(node.get("intent_set") or [])
        for intent in declared:
            if intent not in known_intents:
                report.error("C8", f"{where}:{nid}", f"unknown intent {intent!r}")
        for intent in (node.get("routes") or {}):
            if intent not in declared and intent not in globals_:
                report.error("C8", f"{where}:{nid}",
                             f"routes[{intent}] is not in intent_set and is not global")
        if node["kind"] in LISTENING and not declared:
            report.warn("C8", f"{where}:{nid}", "listening node declares no intent_set")

    # ---- C4 reachability and termination -----------------------------------
    edges = {nid: successors(node, global_targets) for nid, node in nodes.items()}
    seen, stack = set(), [doc["entry"]]
    if doc["entry"] not in nodes:
        report.error("C4", where, f"entry {doc['entry']!r} is not a node")
        return doc, nodes
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        stack.extend(edges[nid])
    for nid in nodes:
        if nid not in seen:
            report.error("C4", f"{where}:{nid}", "unreachable from entry")
    for nid, node in nodes.items():
        if node["kind"] in ("terminal", "transfer"):
            if edges[nid] and node["kind"] == "terminal":
                report.error("C4", f"{where}:{nid}", "terminal node has outgoing transitions")
        elif not edges[nid]:
            report.error("C4", f"{where}:{nid}", "non-terminal node is a dead end")

    # ---- C5 disclosure must-analysis ---------------------------------------
    # played_in[n] = the disclosures guaranteed to have played on EVERY path reaching n.
    # Intersection over predecessors, iterated to a fixpoint. Initialised to the universal set
    # for non-entry nodes so the intersection can only shrink.
    preds = defaultdict(set)
    for nid, targets in edges.items():
        for t in targets:
            preds[t].add(nid)
    every = set()
    for node in nodes.values():
        every |= set(node.get("plays_disclosure") or [])
    entry = doc["entry"]
    played_in = {nid: (set() if nid == entry else set(every)) for nid in nodes}
    for _ in range(len(nodes) + 2):
        changed = False
        for nid in nodes:
            if nid == entry:
                continue
            incoming = [p for p in preds[nid] if p in seen]
            if not incoming:
                new = set()
            else:
                new = set.intersection(
                    *[played_in[p] | set(nodes[p].get("plays_disclosure") or [])
                      for p in incoming])
            if new != played_in[nid]:
                played_in[nid] = new
                changed = True
        if not changed:
            break
    for nid, node in nodes.items():
        if nid not in seen:
            continue
        missing = set(node.get("requires_disclosure") or []) - played_in[nid]
        if missing:
            report.error("C5", f"{where}:{nid}",
                         "reachable without " + ", ".join(sorted(missing)))

    # ---- FAQ scope resolves -------------------------------------------------
    for nid, node in nodes.items():
        for scope in node.get("faq_scope") or []:
            if scope not in faq_ids_by_scope:
                report.error("C1", f"{where}:{nid}", f"faq_scope {scope!r} has no file")

    return doc, nodes


def check_faqs(vars_doc, report):
    ids_by_scope, all_ids = {}, {}
    declared_slots = set(vars_doc["slots"])
    locales = vars_doc["required_locale"]
    for path in sorted((CONTENT / "faq").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        scope = doc["scope"]
        ids_by_scope[scope] = set()
        for entry in doc["entries"]:
            eid = entry["id"]
            where = f"faq/{path.name}:{eid}"
            if eid in all_ids:
                report.error("C7", where, f"duplicate FAQ id, also in {all_ids[eid]}")
            all_ids[eid] = path.name
            ids_by_scope[scope].add(eid)
            for field in ("question", "answer"):
                block = entry.get(field) or {}
                for loc in locales:
                    if loc not in block:
                        report.error("C6", where, f"{field} missing locale {loc!r}")
            for loc, text in (entry.get("answer") or {}).items():
                for slot in SLOT.findall(text):
                    if slot not in declared_slots:
                        report.error("C3", f"{where}:{loc}", f"undeclared slot {{{slot}}}")
                if DIGIT_OUTSIDE_SLOT.search(text):
                    report.error("C10", f"{where}:{loc}", "literal number in an approved answer")
                for phrase in entry.get("never_say") or []:
                    if phrase.lower() in text.lower():
                        report.error("C9", f"{where}:{loc}",
                                     f"answer contains its own never_say phrase {phrase!r}")
    return ids_by_scope


def render(products, faq_ids_by_scope):
    out = ["# Approved Content — rendered view",
           "",
           "> Generated by `tools/validate_content.py --render`. Do not edit by hand;",
           "> edit the YAML under `content/` and re-render.",
           "",
           "**Status: SYNTHETIC.** Every line below is `[TransOrg]`-invented placeholder content,",
           "standing in for the BLC-approved script and the SBIC FAQ glossary, neither of which we",
           "have seen. See open item OI-5.",
           ""]
    for product, (doc, nodes) in products.items():
        out += [f"## {product}", "",
                f"Version {doc['version']} · approval ref `{doc['approval_ref']}` · "
                f"entry `{doc['entry']}` · {len(nodes)} nodes", ""]
        out += ["| Node | Kind | Says (en) | Requires | Plays |", "|---|---|---|---|---|"]
        for nid, node in nodes.items():
            text = (node.get("line") or {}).get("en", "") or "—"
            text = text if len(text) < 90 else text[:87] + "…"
            out.append("| `{}` | {} | {} | {} | {} |".format(
                nid, node["kind"], text.replace("|", "\\|"),
                ", ".join(node.get("requires_disclosure") or []) or "—",
                ", ".join(node.get("plays_disclosure") or []) or "—"))
        out.append("")
    out += ["## FAQ glossary", "",
            "| Scope | Entries |", "|---|---|"]
    for scope, ids in sorted(faq_ids_by_scope.items()):
        out.append(f"| {scope} | {len(ids)} |")
    out += ["", f"**Total routable FAQ entries: {sum(len(v) for v in faq_ids_by_scope.values())}.** ",
            "RESEARCH §2.3 heuristic: <15 routes → LLM directly; 15–50 → embedding router;",
            "50+ → fine-tuned classifier; 100+ non-negotiable. The real glossary size (OI-5)",
            "therefore decides the router architecture, not just the content volume.", ""]
    target = ROOT / "docs" / "SCRIPT.md"
    target.write_text("\n".join(out), encoding="utf-8")
    return target


def main():
    global CONTENT, PRODUCTS
    if "--pack" in sys.argv:
        CONTENT = pathlib.Path(sys.argv[sys.argv.index("--pack") + 1]).resolve()
    manifest = yaml.safe_load((CONTENT / "pack.yaml").read_text(encoding="utf-8"))
    PRODUCTS = tuple(manifest["products"])
    print(f"pack: {manifest['name']} v{manifest['version']} "
          f"({manifest['provenance']}, ref {manifest.get('approval_ref')})")
    print(f"      {CONTENT}")
    print()

    report = Report()
    vars_doc = load("campaign_vars.yaml")
    intents_doc = load("intents.yaml")

    faq_ids_by_scope = check_faqs(vars_doc, report)
    products = {}
    for product in PRODUCTS:
        products[product] = check_product(
            product, vars_doc, intents_doc, faq_ids_by_scope, report)

    # out_of_scope corpus must route somewhere real in every product
    oos_doc = load("out_of_scope.yaml")
    for cat in oos_doc["categories"]:
        target = cat.get("route", oos_doc["default_route"])
        for product, (_, nodes) in products.items():
            if target not in nodes:
                report.error("C2", f"out_of_scope.yaml:{cat['id']}",
                             f"route {target!r} does not exist in {product}")
        if not (cat.get("examples_en") or cat.get("examples_hi_latn")):
            report.warn("C2", f"out_of_scope.yaml:{cat['id']}",
                        "no examples - cannot train OUT_OF_SCOPE as a class")

    for check, where, msg in report.errors:
        print(f"ERROR [{check}] {where}: {msg}")
    for check, where, msg in report.warnings:
        print(f"warn  [{check}] {where}: {msg}")

    total_faq = sum(len(v) for v in faq_ids_by_scope.values())
    total_nodes = sum(len(n) for _, n in products.values())
    print(f"\n{len(PRODUCTS)} products · {total_nodes} nodes · {total_faq} FAQ entries · "
          f"{len(oos_doc['categories'])} out-of-scope categories")
    print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")

    if "--render" in sys.argv and not report.errors:
        print(f"rendered {render(products, faq_ids_by_scope).relative_to(ROOT)}")

    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
