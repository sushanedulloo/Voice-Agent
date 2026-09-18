#!/usr/bin/env python3
"""Turn a client-supplied spreadsheet into a content pack.

    python tools/import_script.py --in incoming/sbic --out packs/sbic-blc-2026-10 \\
                                  --name sbic-blc --approval-ref BLC-2026-1012-FLEXI

Expects three CSVs in --in (export each sheet of whatever workbook they send):

  nodes.csv        node_id, product, kind, text_en, text_hi_latn, next,
                   plays_disclosure, requires_disclosure, never_say, disposition,
                   faq_scope, intent_set, max_visits, on_max_visits, escalate
  transitions.csv  product, node_id, intent, target
  faq.csv          faq_id, scope, question_en, question_hi_latn,
                   answer_en, answer_hi_latn, paraphrases_en, paraphrases_hi_latn

Multi-value cells are pipe-separated: "D01_IDENTITY|D02_RECORDED_LINE".

WHY AN IMPORTER RATHER THAN RETYPING
------------------------------------
The script is a legal artefact. Hand-copying a BLC-approved sentence into YAML is an opportunity
to introduce a typo into an approved disclosure, and nobody would ever find it. Importing keeps
the client's text byte-for-byte, and the validator then proves the resulting graph is sound
before anything runs.

The importer does NOT invent. Missing columns become missing fields, and the pack fails
validation with a specific complaint rather than quietly working. A pack that imports cleanly but
has no OUT_OF_SCOPE route is more dangerous than one that refuses to load.
"""

import argparse
import csv
import pathlib
import shutil
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MULTI = "|"


def split(value):
    return [v.strip() for v in (value or "").split(MULTI) if v.strip()]


def read(path):
    if not path.exists():
        raise SystemExit(f"missing {path.name} in the input directory")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def carried_global_routes(carry: pathlib.Path, product: str) -> dict:
    """Global routes are TransOrg controls, not client content.

    A client spreadsheet has no column for "what happens when the customer says DND at any
    point in the call" - that is our safety wiring, and it is identical across products. So it
    carries across from the reference pack exactly as intents.yaml and disclosures.yaml do,
    rather than being retyped or, worse, left empty.
    """
    path = carry / "script" / f"{product}.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("global_routes") or {}


def build_scripts(nodes, transitions, out_dir, carry):
    by_product = {}
    for row in nodes:
        by_product.setdefault(row["product"], []).append(row)

    routes = {}
    for row in transitions:
        routes.setdefault((row["product"], row["node_id"]), {})[row["intent"]] = row["target"]

    written = []
    for product, rows in by_product.items():
        doc = {
            "product": product,
            "version": "1.0.0",
            "status": "imported",
            "approval_ref": None,          # filled from the manifest by the caller
            "effective_from": None,
            "entry": rows[0]["node_id"],
            "global_routes": carried_global_routes(carry, product),
            "nodes": [],
        }
        for row in rows:
            node = {"id": row["node_id"], "kind": row["kind"]}
            for field, column in (("requires_disclosure", "requires_disclosure"),
                                  ("plays_disclosure", "plays_disclosure"),
                                  ("never_say", "never_say"),
                                  ("faq_scope", "faq_scope"),
                                  ("intent_set", "intent_set")):
                values = split(row.get(column))
                if values:
                    node[field] = values
            if row.get("faq_scope"):
                node["faq_enabled"] = True
            node["line"] = {"en": row.get("text_en", ""),
                            "hi_latn": row.get("text_hi_latn", "")}
            if row.get("next"):
                node["next"] = row["next"]
            if row.get("disposition"):
                node["disposition"] = row["disposition"]
            # Visit caps. Without these the silence-timeout terminal is unreachable and the bot
            # re-prompts forever - found by the validator on the first round-trip, not by review.
            if row.get("max_visits"):
                node["max_visits"] = int(row["max_visits"])
            if row.get("on_max_visits"):
                node["on_max_visits"] = row["on_max_visits"]
            if str(row.get("escalate", "")).strip().lower() in ("1", "true", "yes"):
                node["escalate"] = True
            node_routes = routes.get((product, row["node_id"]))
            if node_routes:
                node["routes"] = node_routes
            doc["nodes"].append(node)

        path = out_dir / "script" / f"{product}.yaml"
        path.write_text(
            "# IMPORTED from client spreadsheet by tools/import_script.py. Do not hand-edit -\n"
            "# re-import instead, so the client's approved text stays the single source.\n\n"
            + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8")
        written.append((product, len(doc["nodes"])))
    return written


def build_faq(rows, out_dir):
    by_scope = {}
    for row in rows:
        by_scope.setdefault(row["scope"], []).append(row)

    written = []
    for scope, entries in by_scope.items():
        doc = {"scope": scope, "version": "1.0.0", "status": "imported",
               "approval_ref": None, "entries": []}
        for row in entries:
            entry = {
                "id": row["faq_id"],
                "question": {"en": row.get("question_en", ""),
                             "hi_latn": row.get("question_hi_latn", "")},
                "answer": {"en": row.get("answer_en", ""),
                           "hi_latn": row.get("answer_hi_latn", "")},
            }
            for locale in ("en", "hi_latn"):
                paras = split(row.get(f"paraphrases_{locale}"))
                if paras:
                    entry[f"paraphrases_{locale}"] = paras
            doc["entries"].append(entry)
        (out_dir / "faq" / f"{scope}.yaml").write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8")
        written.append((scope, len(doc["entries"])))
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--approval-ref", required=True)
    ap.add_argument("--carry-from", default="content",
                    help="pack to copy non-script assets from (intents, disclosures, "
                         "out_of_scope, campaign_vars). These are ours, not the client's.")
    args = ap.parse_args()

    src, out = pathlib.Path(args.src), pathlib.Path(args.out)
    carry = pathlib.Path(args.carry_from)
    out.mkdir(parents=True, exist_ok=True)
    (out / "script").mkdir(exist_ok=True)
    (out / "faq").mkdir(exist_ok=True)

    # These four are TransOrg-authored engineering assets, not client content: the intent
    # vocabulary, the mandatory-disclosure text, the out-of-scope corpus and the variable
    # declarations. They carry across unchanged so an import replaces the client's words
    # without discarding our controls.
    for name in ("intents.yaml", "disclosures.yaml", "out_of_scope.yaml",
                 "campaign_vars.yaml", "handoff.yaml", "acceptance.yaml", "schema.md"):
        if (carry / name).exists():
            shutil.copy2(carry / name, out / name)

    nodes = read(src / "nodes.csv")
    transitions = read(src / "transitions.csv")
    faq = read(src / "faq.csv")

    scripts = build_scripts(nodes, transitions, out, carry)
    faqs = build_faq(faq, out)

    manifest = {
        "name": args.name, "version": "1.0.0", "provenance": "blc-approved",
        "approval_ref": args.approval_ref, "approved_by": None,
        "effective_from": None, "expires_on": None,
        "description": f"Imported from {src} by tools/import_script.py.",
        "products": [p for p, _ in scripts],
        "locales": ["en", "hi_latn"],
        "files": {"campaign_vars": "campaign_vars.yaml", "disclosures": "disclosures.yaml",
                  "intents": "intents.yaml", "out_of_scope": "out_of_scope.yaml",
                  "handoff": "handoff.yaml", "acceptance": "acceptance.yaml",
                  "script_dir": "script", "faq_dir": "faq"},
    }
    (out / "pack.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")

    for product, count in scripts:
        print(f"  script  {product:16} {count:4} nodes")
    for scope, count in faqs:
        print(f"  faq     {scope:16} {count:4} entries")
    print(f"\n  -> {out}")
    print(f"\n  global_routes is EMPTY in each script - a spreadsheet has no column for")
    print(f"  'what happens when the customer says DNC at any point'. Author it, then:")
    print(f"      python tools/validate_content.py --pack {out}")
    print(f"  The pack will not load until it is right, which is the intended behaviour.")


if __name__ == "__main__":
    main()
