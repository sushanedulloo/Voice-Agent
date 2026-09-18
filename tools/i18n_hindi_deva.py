#!/usr/bin/env python3
"""Devanagari Hindi as a proper spoken locale.

    python tools/i18n_hindi_deva.py

WHY THIS EXISTS
---------------
The pack shipped Hindi as `hi_latn` - romanised - because it was readable during development.
That turned out to be wrong at BOTH ends of the pipeline:

  ASR   indic-conformer emits Devanagari. Romanised examples scored 0.000 against it, so every
        Hindi turn deflected to a human. (Already patched by adding examples_hi anchors.)
  TTS   parler and espeak both phonemise Hindi from Devanagari. Given Latin text they fall back
        to spelling it - measurably, the same sentence rendered 19% longer romanised than in
        Devanagari.

So `hi` becomes the spoken locale. `hi_latn` stays in the pack: it costs nothing, it is what a
demo operator types, and it gives the router a second set of anchors for romanised ASR output -
which is exactly what a code-mixed Hinglish transcript looks like.

Same content, correct script. Nothing here is a new translation.
"""

import io
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SLOT = re.compile(r"\{([a-z_]+)\}")

LINES = {
 "Hello, good day.": "नमस्ते.",
 "Am I speaking with {customer_first_name}?": "क्या मैं {customer_first_name} जी से बात कर रही हूँ?",
 "I am calling about an offer available on your card. It will take about a minute.":
   "मैं आपके कार्ड पर उपलब्ध एक ऑफर के बारे में कॉल कर रही हूँ. सिर्फ़ एक मिनट लगेगा.",
 "I am calling about your card limit. It will take less than a minute.":
   "मैं आपके कार्ड की लिमिट के बारे में कॉल कर रही हूँ. एक मिनट से भी कम लगेगा.",
 "I am calling about an additional card available to you. It will take about a minute.":
   "मैं आपके लिए उपलब्ध एक अतिरिक्त कार्ड के बारे में कॉल कर रही हूँ. लगभग एक मिनट लगेगा.",
 "You are eligible to convert purchases above {min_txn_amt} rupees into easy monthly instalments. On your card, up to {eligible_amount} rupees can be converted over {tenure_options}.":
   "आप {min_txn_amt} रुपये से ऊपर की ख़रीदारी को आसान मासिक क़िस्तों में बदल सकते हैं. आपके कार्ड पर {eligible_amount} रुपये तक, {tenure_options} में बदला जा सकता है.",
 "Based on your card usage, your credit limit can be increased from {current_limit} rupees to {enhanced_limit} rupees.":
   "आपके कार्ड उपयोग के आधार पर, आपकी क्रेडिट लिमिट {current_limit} रुपये से बढ़कर {enhanced_limit} रुपये हो सकती है.",
 "You are eligible for an additional {brand_name} card, the {offered_card_name}, which offers {headline_benefit}.":
   "आप एक अतिरिक्त {brand_name} कार्ड के लिए पात्र हैं, {offered_card_name}, जिसमें {headline_benefit} मिलता है.",
 "At a tenure of {tenure_months} months, your indicative instalment would be about {indicative_emi} rupees per month.":
   "{tenure_months} महीने की अवधि पर, आपकी अनुमानित क़िस्त हर महीने लगभग {indicative_emi} रुपये होगी.",
 "This offer is open for {offer_valid_days} days.": "यह ऑफर {offer_valid_days} दिन तक उपलब्ध है.",
 "The card is issued subject to approval.": "कार्ड मंज़ूरी के अधीन जारी किया जाता है.",
 "Shall I connect you to our advisor to take this forward?":
   "आगे बढ़ने के लिए क्या मैं आपको हमारे एडवाइज़र से जोड़ूँ?",
 "Shall I connect you to our advisor to complete this?":
   "इसे पूरा करने के लिए क्या मैं आपको हमारे एडवाइज़र से जोड़ूँ?",
 "Thank you. Please stay on the line.": "धन्यवाद. कृपया लाइन पर बने रहिए.",
 "Of course. The offer is open for {offer_valid_days} days. Would you prefer that our advisor explains the details now, or should we call you back?":
   "ज़रूर. यह ऑफर {offer_valid_days} दिन तक उपलब्ध है. क्या हमारे एडवाइज़र अभी डिटेल बताएँ, या हम आपको दोबारा कॉल करें?",
 "Of course. The offer stays open for {offer_valid_days} days. Would you like our advisor to explain it now, or should we call you back?":
   "ज़रूर. यह ऑफर {offer_valid_days} दिन तक रहेगा. क्या हमारे एडवाइज़र अभी समझाएँ, या हम दोबारा कॉल करें?",
 "Of course. Would you prefer that our advisor explains the details now, or should we call you back?":
   "ज़रूर. क्या हमारे एडवाइज़र अभी डिटेल बताएँ, या हम आपको दोबारा कॉल करें?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can also verify this offer on your {brand_name} app, or by calling the number printed on the back of your card. Shall I continue?":
   "यह सही सवाल है. मैं आपसे कोई कार्ड नंबर, पिन या ओटीपी नहीं माँग रही हूँ, और न कभी माँगूँगी. आप यह ऑफर अपने {brand_name} ऐप पर, या कार्ड के पीछे लिखे नंबर पर कॉल करके भी जाँच सकते हैं. क्या मैं आगे बढ़ूँ?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can verify this on your {brand_name} app, or on the number printed on the back of your card. Shall I continue?":
   "यह सही सवाल है. मैं आपसे कोई कार्ड नंबर, पिन या ओटीपी नहीं माँग रही हूँ, और न कभी माँगूँगी. आप इसे अपने {brand_name} ऐप पर, या कार्ड के पीछे लिखे नंबर पर जाँच सकते हैं. क्या मैं आगे बढ़ूँ?",
 "I am calling on the number registered with your {brand_name} card account. If you would prefer not to receive such calls, I can note that right away.":
   "मैं आपके {brand_name} कार्ड अकाउंट पर रजिस्टर्ड नंबर पर कॉल कर रही हूँ. अगर आप ऐसे कॉल नहीं चाहते, तो मैं अभी नोट कर सकती हूँ.",
 "That is understandable. A higher limit does not change what you spend, and there is no charge for the increase itself. Would you still like to hear the details from our advisor?":
   "यह समझ में आता है. ज़्यादा लिमिट से आपका ख़र्च नहीं बढ़ता, और लिमिट बढ़ाने का कोई चार्ज नहीं है. क्या आप फिर भी हमारे एडवाइज़र से डिटेल सुनना चाहेंगे?",
 "Many customers do hold more than one card, and each card carries its own benefits. Would you like our advisor to explain how this one differs from your existing card?":
   "कई ग्राहक एक से ज़्यादा कार्ड रखते हैं, और हर कार्ड के अपने फ़ायदे होते हैं. क्या हमारे एडवाइज़र बताएँ कि यह आपके मौजूदा कार्ड से कैसे अलग है?",
 "Certainly. We will call you back at a more convenient time.":
   "ज़रूर. हम आपको किसी सुविधाजनक समय पर दोबारा कॉल करेंगे.",
 "I apologise for the inconvenience. I will update our records.":
   "असुविधा के लिए खेद है. मैं हमारे रिकॉर्ड अपडेट कर दूँगी.",
 "I understand. May we call you back later today?":
   "मैं समझ सकती हूँ. क्या हम आज बाद में कॉल करें?",
 "That is perfectly alright. Thank you for your time, and have a good day.":
   "कोई बात नहीं. आपके समय के लिए धन्यवाद, आपका दिन अच्छा हो.",
 "Thank you. Have a good day.": "धन्यवाद. आपका दिन अच्छा हो.",
 "I have noted your request. You will not receive further promotional calls from us. Thank you.":
   "मैंने आपका अनुरोध नोट कर लिया है. आपको आगे हमसे प्रमोशनल कॉल नहीं आएँगे. धन्यवाद.",
 "Thank you, and sorry for the disturbance.": "धन्यवाद, और परेशानी के लिए खेद है.",
 "I am ending the call now. Thank you.": "मैं अब कॉल समाप्त कर रही हूँ. धन्यवाद.",
 "I am unable to hear you. We will try again another time. Thank you.":
   "मैं आपको सुन नहीं पा रही हूँ. हम किसी और समय कोशिश करेंगे. धन्यवाद.",
 "I am sorry, I could not hear you. Are you still there?":
   "माफ़ कीजिए, मुझे सुनाई नहीं दिया. क्या आप लाइन पर हैं?",
 "Certainly.": "ज़रूर.",
 "That is a good question, and I would rather our advisor answer it properly for you.":
   "यह अच्छा सवाल है, और बेहतर होगा कि हमारे एडवाइज़र आपको इसका सही जवाब दें.",
 "I am {agent_display_name}, calling on behalf of {brand_name}.":
   "मैं {agent_display_name}, {brand_name} की तरफ़ से कॉल कर रही हूँ.",
 "This call is recorded for quality and training purposes.":
   "यह कॉल क्वालिटी और ट्रेनिंग के लिए रिकॉर्ड की जा रही है.",
 "This conversion carries interest of {roi_annual_pct} percent per annum and a one-time processing fee of {processing_fee} rupees. Goods and services tax applies as per government rules.":
   "इस कन्वर्ज़न पर {roi_annual_pct} प्रतिशत सालाना ब्याज और {processing_fee} रुपये की एक बार की प्रोसेसिंग फ़ीस लगती है. जीएसटी सरकारी नियमों के अनुसार लगेगा.",
 "The revised limit is subject to the terms and conditions of your card agreement.":
   "संशोधित लिमिट आपके कार्ड एग्रीमेंट के नियमों और शर्तों के अधीन है.",
 "This card carries a joining fee of {joining_fee} rupees and an annual fee of {annual_fee} rupees, which is reversed on {fee_waiver_condition}.":
   "इस कार्ड पर {joining_fee} रुपये जॉइनिंग फ़ीस और {annual_fee} रुपये सालाना फ़ीस है, जो {fee_waiver_condition} पर वापस कर दी जाती है.",
 "I will now connect you to our advisor, who will confirm your details and complete the process.":
   "मैं अब आपको हमारे एडवाइज़र से जोड़ रही हूँ, जो आपकी डिटेल कन्फ़र्म करके प्रक्रिया पूरी करेंगे.",
}

BACKCHANNELS = {
 "acknowledge": ["जी.", "जी हाँ.", "ठीक है.", "बिल्कुल."],
 "before_answer": ["जी ज़रूर.", "हाँ, बताती हूँ.", "अच्छा सवाल है."],
 "soften": ["समझ सकती हूँ.", "कोई बात नहीं."],
 "thinking": ["एक सेकंड.", "ज़रा रुकिए."],
 "language_switched": ["जी बिल्कुल, हम हिंदी में बात करते हैं."],
}


def main():
    content = ROOT / "content"
    problems, n_lines, n_faq = [], 0, 0

    def check(english, hindi):
        if set(SLOT.findall(english)) != set(SLOT.findall(hindi)):
            problems.append(f"slot mismatch: {english[:60]}")
            return None
        return hindi

    # scripts
    for path in sorted((content / "script").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for node in doc["nodes"]:
            line = node.get("line") or {}
            english = line.get("en", "").strip()
            if node.get("kind") == "transfer":
                line["hi"] = ""
                continue
            got = LINES.get(english)
            if got and check(english, got):
                line["hi"] = got
                n_lines += 1
        head = path.read_text(encoding="utf-8").split("product:")[0]
        path.write_text(head + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True,
                                              width=200), encoding="utf-8")

    # disclosures
    dp = content / "disclosures.yaml"
    ddoc = yaml.safe_load(dp.read_text(encoding="utf-8"))
    for spec in ddoc["disclosures"].values():
        english = " ".join(spec["line"]["en"].split())
        got = LINES.get(english)
        if got and check(english, got):
            spec["line"]["hi"] = got
            n_lines += 1
    head = dp.read_text(encoding="utf-8").split("version:")[0]
    dp.write_text(head + yaml.safe_dump(ddoc, sort_keys=False, allow_unicode=True, width=200),
                  encoding="utf-8")

    # FAQ is deliberately NOT filled here. Copying hi_latn into `hi` would hand the renderer
    # 108 Devanagari-labelled clips containing romanised text, which parler would mispronounce -
    # and nothing would fail, it would just sound wrong. `hi` stays out of required_locale until
    # tools/i18n_hindi_faq.py supplies real Devanagari, and C6 enforces that.

    # backchannels
    bp = content / "backchannels.yaml"
    bdoc = yaml.safe_load(bp.read_text(encoding="utf-8"))
    for cat, tokens in BACKCHANNELS.items():
        bdoc["tokens"].setdefault(cat, {})["hi"] = tokens
    head = bp.read_text(encoding="utf-8").split("version:")[0]
    bp.write_text(head + yaml.safe_dump(bdoc, sort_keys=False, allow_unicode=True, width=160),
                  encoding="utf-8")

    for p in problems:
        print("  " + p)
    print(f"  {n_lines} lines and disclosures written in Devanagari")
    print("  FAQ not yet in Devanagari - `hi` stays out of required_locale until it is.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
