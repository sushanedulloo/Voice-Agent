#!/usr/bin/env python3
"""Generate a synthetic calling base.

    python tools/make_base.py --rows 5000 --out runs/base.csv

Shaped like what actually arrives (CH-* step 6): DNCR-scrubbed, one masked reference per record,
plus that customer's offer variables.

The one exception is `customer_first_name`, because a nameless greeting sounds like a robocall.
It is marked `pii: true` in campaign_vars.yaml, which means it is spoken and then dropped -
Session.handoff_payload refuses to emit it and tests/test_engine.py fails if it appears. There is
no mobile number, no address, no date of birth and no card number here, and no column to put one
in: the schema is checked against campaign_vars.yaml before a row is written.

In production the name arrives per call from the partner's dialer. We never hold a file of them;
this file is a simulation of their side.

Every value is invented. The distributions below are guesses, marked as such, and exist so the
funnel has something to run on before a real base is shared (DELIVERY-PLAN 0.3).
"""

import argparse
import csv
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from engine import Content                                       # noqa: E402

# Guesses. Replace with the real campaign mix.
PRODUCT_MIX = {"flexipay": 0.55, "clip": 0.30, "multicarding": 0.15}
LOCALE_MIX = {"en": 0.40, "hi": 0.60}   # hi = Devanagari, the spoken locale

# Names, by the language the call is placed in. A Hindi-language call to a customer in Chennai
# with a Tamil name is a detail a reviewer notices and it makes the whole demo feel invented, so
# names track the locale. CH-* step 1 says the base is "segmented by zones", which is why zone
# is carried here too.
#
# These are INVENTED. No real cardholder appears in this file and there is nowhere to put one -
# the schema is checked against campaign_vars.yaml before anything is written.
NAMES = {
    "hi": ["Tushar", "Vishad", "Sushane", "Rohit", "Ankit", "Priyanka", "Neha",
                "Deepak", "Manish", "Shweta", "Rahul", "Pooja", "Amit", "Kavita",
                "Sandeep", "Gaurav", "Ritu", "Nikhil", "Swati", "Arjun"],
    "en":      ["Tushar", "Vishad", "Sushane", "Karan", "Aditya", "Meghna", "Ishaan",
                "Rhea", "Varun", "Tanya", "Siddharth", "Ananya", "Kabir", "Nisha",
                "Rajat", "Aparna", "Dhruv", "Sana", "Vivek", "Divya"],
}
ZONES = {"hi": ["North", "North", "West", "Central", "East"],
         "en": ["West", "South", "North", "West", "South"]}

FIELDS_BY_PRODUCT = {
    "flexipay": ["min_txn_amt", "eligible_amount", "tenure_months", "tenure_options",
                 "roi_annual_pct", "processing_fee", "indicative_emi", "offer_valid_days"],
    "clip": ["current_limit", "enhanced_limit", "offer_valid_days"],
    "multicarding": ["offered_card_name", "joining_fee", "annual_fee",
                     "fee_waiver_condition", "headline_benefit"],
}
COMMON = ["brand_name", "agent_display_name"]

CARDS = [("SimplyCLICK", 499, 499, "annual spends of one lakh rupees",
          "ten times reward points on online spends"),
         ("SimplySAVE", 499, 499, "annual spends of one lakh rupees",
          "ten reward points per one hundred and fifty rupees on groceries"),
         ("PRIME", 2999, 2999, "annual spends of three lakh rupees",
          "complimentary airport lounge access"),
         ("CASHBACK", 999, 999, "annual spends of two lakh rupees",
          "five percent cashback on online spends")]

# Spoken, not written. TTS reads "3, 6, 9 or 12 months" as digits and it sounds like a form;
# a human agent says it in words. Amounts stay numeric - an offer value must be unambiguous.
TENURE_WORDS = {3: "three", 6: "six", 9: "nine", 12: "twelve", 18: "eighteen", 24: "twenty-four"}


def pick(mix, rng):
    roll, cum = rng.random(), 0.0
    for key, share in mix.items():
        cum += share
        if roll <= cum:
            return key
    return next(iter(mix))


def row(i, rng):
    product = pick(PRODUCT_MIX, rng)
    locale = pick(LOCALE_MIX, rng)
    rec = {
        "masked_ref_id": f"SBIC-{rng.randrange(0x1000, 0xFFFF):04X}-{i:06d}",
        "product": product,
        "locale": locale,
        "zone": rng.choice(ZONES[locale]),
        # Spoken on the call, never logged. campaign_vars.yaml marks it pii: true and
        # Session.handoff_payload refuses to emit it. See tests/test_engine.py.
        "customer_first_name": rng.choice(NAMES[locale]),
        "brand_name": "SBI Card",
        "agent_display_name": rng.choice(["Priya", "Anjali", "Meera", "Sneha"]),
        "offer_valid_days": rng.choice([7, 15, 30]),
    }
    if product == "flexipay":
        eligible = rng.randrange(8, 240) * 1000
        # The tenure offered must appear in the tenure list the bot reads out. A record that
        # offers eighteen months while the script says "three, six, nine or twelve" is exactly
        # the incoherence a reviewer spots and it makes the whole demo look invented.
        options = rng.choice([[3, 6, 9], [3, 6, 9, 12], [6, 12, 18], [12, 18, 24]])
        tenure = rng.choice(options)
        spoken = ", ".join(TENURE_WORDS[m] for m in options[:-1]) + f" or {TENURE_WORDS[options[-1]]}"
        roi = rng.choice([13.0, 14.5, 16.0, 18.0])
        rec.update(min_txn_amt=2500, eligible_amount=eligible, tenure_months=tenure,
                   tenure_options=f"{spoken} months", roi_annual_pct=roi,
                   processing_fee=rng.choice([99, 149, 199]),
                   indicative_emi=int(round(eligible / tenure * (1 + roi / 100 / 2), -1)))
    elif product == "clip":
        current = rng.randrange(5, 40) * 10000
        rec.update(current_limit=current,
                   enhanced_limit=int(current * rng.uniform(1.4, 2.6) // 10000 * 10000))
    else:
        name, joining, annual, waiver, benefit = rng.choice(CARDS)
        rec.update(offered_card_name=name, joining_fee=joining, annual_fee=annual,
                   fee_waiver_condition=waiver, headline_benefit=benefit)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=2000)
    ap.add_argument("--out", default="runs/base.csv")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    content = Content()
    declared = set(content.vars["slots"])

    rows = [row(i, rng) for i in range(1, args.rows + 1)]
    columns = ["masked_ref_id", "product", "locale"] + sorted(
        {k for r in rows for k in r} - {"masked_ref_id", "product", "locale"})

    unknown = set(columns) - declared - {"masked_ref_id", "product", "locale", "zone"}
    if unknown:
        raise SystemExit(f"base carries columns not declared in campaign_vars.yaml: {unknown}")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, restval="")
        writer.writeheader()
        writer.writerows(rows)

    mix = {}
    for r in rows:
        mix[r["product"]] = mix.get(r["product"], 0) + 1
    print(f"{len(rows)} records -> {out}")
    print("  mix:", ", ".join(f"{k} {v}" for k, v in sorted(mix.items())))
    print("  every column is declared in campaign_vars.yaml")
    print("  customer_first_name is marked pii: true - spoken on the call, stripped from the")
    print("  handoff payload and the audit trail. In production it arrives per call from the")
    print("  partner's dialer; we never hold a file of them.")


if __name__ == "__main__":
    main()
