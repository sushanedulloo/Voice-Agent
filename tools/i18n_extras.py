#!/usr/bin/env python3
"""Backchannels and out-of-scope examples for the seven remaining languages.

    python tools/i18n_extras.py

BACKCHANNELS are the naturalness layer - short acknowledgement tokens played before the
substantive line. They carry no claim and quantify nothing, so a wrong pick is harmless, which
is exactly why they are the cheapest naturalness available inside ADR-002.

OUT-OF-SCOPE examples are the opposite: they are safety-critical. Every one of them is a
question the bot must REFUSE to answer, and a language without them will confidently misroute
an off-glossary question to the nearest in-scope answer. On a credit product that is
mis-selling (RESEARCH 2.4). A language is not safe to run until these exist in it.

Native script throughout, because that is what the ASR emits.
"""

import io
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

BACKCHANNELS = {
 "mr": {"acknowledge": ["हो.", "बरं.", "ठीक आहे.", "नक्की."],
        "before_answer": ["हो नक्की.", "सांगते.", "चांगला प्रश्न आहे."],
        "soften": ["समजू शकते.", "काही हरकत नाही."],
        "thinking": ["एक सेकंद.", "जरा थांबा."],
        "language_switched": ["हो, आपण मराठीत बोलूया."]},
 "gu": {"acknowledge": ["હા.", "સારું.", "ઠીક છે.", "ચોક્કસ."],
        "before_answer": ["હા ચોક્કસ.", "કહું છું.", "સારો પ્રશ્ન છે."],
        "soften": ["સમજી શકું છું.", "કોઈ વાંધો નથી."],
        "thinking": ["એક સેકન્ડ.", "જરા થોભો."],
        "language_switched": ["હા, આપણે ગુજરાતીમાં વાત કરીએ."]},
 "bn": {"acknowledge": ["হ্যাঁ.", "আচ্ছা.", "ঠিক আছে.", "অবশ্যই."],
        "before_answer": ["হ্যাঁ অবশ্যই.", "বলছি.", "ভালো প্রশ্ন."],
        "soften": ["বুঝতে পারছি.", "কোনো সমস্যা নেই."],
        "thinking": ["এক সেকেন্ড.", "একটু দাঁড়ান."],
        "language_switched": ["হ্যাঁ, আমরা বাংলায় কথা বলি."]},
 "ta": {"acknowledge": ["ஆமா.", "சரி.", "ஓகே.", "கண்டிப்பா."],
        "before_answer": ["ஆமா கண்டிப்பா.", "சொல்றேன்.", "நல்ல கேள்வி."],
        "soften": ["புரியுது.", "பரவாயில்ல."],
        "thinking": ["ஒரு நிமிஷம்.", "கொஞ்சம் இருங்க."],
        "language_switched": ["சரி, நாம தமிழ்ல பேசலாம்."]},
 "te": {"acknowledge": ["అవును.", "సరే.", "ఓకే.", "తప్పకుండా."],
        "before_answer": ["అవును తప్పకుండా.", "చెప్తాను.", "మంచి ప్రశ్న."],
        "soften": ["అర్థమైంది.", "ఫర్వాలేదు."],
        "thinking": ["ఒక సెకను.", "కొంచెం ఆగండి."],
        "language_switched": ["సరే, మనం తెలుగులో మాట్లాడదాం."]},
 "kn": {"acknowledge": ["ಹೌದು.", "ಸರಿ.", "ಓಕೆ.", "ಖಂಡಿತ."],
        "before_answer": ["ಹೌದು ಖಂಡಿತ.", "ಹೇಳ್ತೇನೆ.", "ಒಳ್ಳೆಯ ಪ್ರಶ್ನೆ."],
        "soften": ["ಅರ್ಥವಾಗುತ್ತೆ.", "ಪರವಾಗಿಲ್ಲ."],
        "thinking": ["ಒಂದು ಸೆಕೆಂಡ್.", "ಸ್ವಲ್ಪ ನಿಲ್ಲಿ."],
        "language_switched": ["ಸರಿ, ನಾವು ಕನ್ನಡದಲ್ಲಿ ಮಾತಾಡೋಣ."]},
 "ml": {"acknowledge": ["അതെ.", "ശരി.", "ഓകെ.", "തീർച്ചയായും."],
        "before_answer": ["അതെ തീർച്ചയായും.", "പറയാം.", "നല്ല ചോദ്യം."],
        "soften": ["മനസ്സിലാകുന്നു.", "കുഴപ്പമില്ല."],
        "thinking": ["ഒരു സെക്കൻഡ്.", "അല്പം നിൽക്കൂ."],
        "language_switched": ["ശരി, നമുക്ക് മലയാളത്തിൽ സംസാരിക്കാം."]},
}

# Only the categories that carry real risk are translated in full. The lexically-adjacent ones -
# cash advance, other credit products, forex, fraud, complaints - are the ones that misroute.
OOS = {
 "mr": {
  "OOS_CASH_ADVANCE": ["कॅश काढल्यावर किती व्याज लागतं", "या कार्डवर कॅश मिळेल का", "एटीएम मधून पैसे काढता येतील का"],
  "OOS_OTHER_CREDIT_PRODUCTS": ["पर्सनल लोन मिळेल का", "होम लोन देता का", "कार लोनचा रेट काय आहे"],
  "OOS_INSURANCE": ["या कार्डवर इन्शुरन्स आहे का", "मला पॉलिसी घ्यायची आहे"],
  "OOS_DISPUTE_OR_FRAUD": ["मी हा ट्रान्झॅक्शन केला नाही", "माझं कार्ड कोणीतरी वापरलं", "माझं कार्ड हरवलं आहे"],
  "OOS_ACCOUNT_SERVICING": ["माझा पत्ता बदलायचा आहे", "कार्ड ब्लॉक करा", "माझं बॅलन्स किती आहे"],
  "OOS_FOREX_AND_CHARGES": ["परदेशात हे कार्ड चालेल का", "फॉरेक्स चार्ज किती आहे", "लेट पेमेंट चार्ज किती"],
  "OOS_COMPLAINT_OR_LEGAL": ["मला तक्रार करायची आहे", "मी कायदेशीर कारवाई करेन", "तुमच्या मॅनेजरशी बोलायचं आहे"],
  "OOS_FINANCIAL_ADVICE": ["मी घेऊ का नको", "तुम्ही असता तर काय केलं असतं", "माझ्यासाठी हे योग्य आहे का"],
  "OOS_PII_SOLICITATION": ["माझा कार्ड नंबर आहे", "ओटीपी सांगतो", "माझा पिन आहे"],
  "OOS_REWARDS": ["माझे किती रिवॉर्ड पॉइंट्स आहेत", "पॉइंट्स कसे वापरायचे"],
  "OOS_SMALL_TALK": ["तुमचं नाव काय आहे", "तुम्ही कुठून आहात"],
 },
 "gu": {
  "OOS_CASH_ADVANCE": ["કેશ ઉપાડવા પર કેટલું વ્યાજ લાગે", "આ કાર્ડ પર કેશ મળશે", "એટીએમમાંથી પૈસા ઉપાડી શકાય"],
  "OOS_OTHER_CREDIT_PRODUCTS": ["પર્સનલ લોન મળશે", "હોમ લોન આપો છો", "કાર લોનનો રેટ શું છે"],
  "OOS_INSURANCE": ["આ કાર્ડ પર ઇન્શ્યોરન્સ છે", "મારે પોલિસી લેવી છે"],
  "OOS_DISPUTE_OR_FRAUD": ["મેં આ ટ્રાન્ઝેક્શન નથી કર્યું", "મારું કાર્ડ કોઈએ વાપર્યું", "મારું કાર્ડ ખોવાઈ ગયું"],
  "OOS_ACCOUNT_SERVICING": ["મારું સરનામું બદલવું છે", "કાર્ડ બ્લોક કરો", "મારું બેલેન્સ કેટલું છે"],
  "OOS_FOREX_AND_CHARGES": ["વિદેશમાં આ કાર્ડ ચાલશે", "ફોરેક્સ ચાર્જ કેટલો છે", "લેટ પેમેન્ટ ચાર્જ કેટલો"],
  "OOS_COMPLAINT_OR_LEGAL": ["મારે ફરિયાદ કરવી છે", "હું કાનૂની પગલાં લઈશ", "તમારા મેનેજર સાથે વાત કરવી છે"],
  "OOS_FINANCIAL_ADVICE": ["મારે લેવું કે નહીં", "તમે હોત તો શું કરત", "મારા માટે આ યોગ્ય છે"],
  "OOS_PII_SOLICITATION": ["મારો કાર્ડ નંબર છે", "ઓટીપી કહું છું", "મારો પિન છે"],
  "OOS_REWARDS": ["મારા કેટલા રિવોર્ડ પોઈન્ટ છે", "પોઈન્ટ કેવી રીતે વાપરવા"],
  "OOS_SMALL_TALK": ["તમારું નામ શું છે", "તમે ક્યાંથી છો"],
 },
 "bn": {
  "OOS_CASH_ADVANCE": ["ক্যাশ তুললে কত সুদ লাগে", "এই কার্ডে ক্যাশ পাওয়া যাবে", "এটিএম থেকে টাকা তোলা যাবে"],
  "OOS_OTHER_CREDIT_PRODUCTS": ["পার্সোনাল লোন পাওয়া যাবে", "হোম লোন দেন", "কার লোনের রেট কত"],
  "OOS_INSURANCE": ["এই কার্ডে ইন্স্যুরেন্স আছে", "আমি পলিসি নিতে চাই"],
  "OOS_DISPUTE_OR_FRAUD": ["আমি এই লেনদেন করিনি", "আমার কার্ড কেউ ব্যবহার করেছে", "আমার কার্ড হারিয়ে গেছে"],
  "OOS_ACCOUNT_SERVICING": ["আমার ঠিকানা বদলাতে হবে", "কার্ড ব্লক করুন", "আমার ব্যালেন্স কত"],
  "OOS_FOREX_AND_CHARGES": ["বিদেশে এই কার্ড চলবে", "ফরেক্স চার্জ কত", "লেট পেমেন্ট চার্জ কত"],
  "OOS_COMPLAINT_OR_LEGAL": ["আমি অভিযোগ করতে চাই", "আমি আইনি ব্যবস্থা নেব", "আপনাদের ম্যানেজারের সাথে কথা বলব"],
  "OOS_FINANCIAL_ADVICE": ["আমার নেওয়া উচিত কিনা", "আপনি হলে কী করতেন", "এটা আমার জন্য ঠিক হবে"],
  "OOS_PII_SOLICITATION": ["আমার কার্ড নম্বর হল", "ওটিপি বলছি", "আমার পিন হল"],
  "OOS_REWARDS": ["আমার কত রিওয়ার্ড পয়েন্ট আছে", "পয়েন্ট কীভাবে ব্যবহার করব"],
  "OOS_SMALL_TALK": ["আপনার নাম কী", "আপনি কোথা থেকে"],
 },
 "ta": {
  "OOS_CASH_ADVANCE": ["கேஷ் எடுத்தா எவ்வளவு வட்டி", "இந்த கார்டுல கேஷ் கிடைக்குமா", "ஏடிஎம்ல பணம் எடுக்க முடியுமா"],
  "OOS_OTHER_CREDIT_PRODUCTS": ["பர்சனல் லோன் கிடைக்குமா", "ஹோம் லோன் தருவீங்களா", "கார் லோன் ரேட் என்ன"],
  "OOS_INSURANCE": ["இந்த கார்டுல இன்ஷூரன்ஸ் இருக்கா", "எனக்கு பாலிசி வேணும்"],
  "OOS_DISPUTE_OR_FRAUD": ["நான் இந்த டிரான்சாக்ஷன் பண்ணல", "என் கார்டை யாரோ யூஸ் பண்ணிட்டாங்க", "என் கார்டு தொலைஞ்சு போச்சு"],
  "OOS_ACCOUNT_SERVICING": ["என் அட்ரஸ் மாத்தணும்", "கார்டை பிளாக் பண்ணுங்க", "என் பேலன்ஸ் எவ்வளவு"],
  "OOS_FOREX_AND_CHARGES": ["வெளிநாட்டுல இந்த கார்டு வேலை செய்யுமா", "ஃபாரெக்ஸ் சார்ஜ் எவ்வளவு", "லேட் பேமெண்ட் சார்ஜ் எவ்வளவு"],
  "OOS_COMPLAINT_OR_LEGAL": ["நான் புகார் கொடுக்கணும்", "நான் சட்ட நடவடிக்கை எடுப்பேன்", "உங்க மேனேஜர்கிட்ட பேசணும்"],
  "OOS_FINANCIAL_ADVICE": ["நான் எடுக்கலாமா வேணாமா", "நீங்க இருந்தா என்ன பண்ணுவீங்க", "இது எனக்கு நல்லதா"],
  "OOS_PII_SOLICITATION": ["என் கார்டு நம்பர்", "ஓடிபி சொல்றேன்", "என் பின் நம்பர்"],
  "OOS_REWARDS": ["என் ரிவார்ட் பாயின்ட் எவ்வளவு", "பாயின்ட் எப்படி யூஸ் பண்றது"],
  "OOS_SMALL_TALK": ["உங்க பேரு என்ன", "நீங்க எங்க இருந்து"],
 },
 "te": {
  "OOS_CASH_ADVANCE": ["క్యాష్ తీస్తే ఎంత వడ్డీ", "ఈ కార్డ్ పై క్యాష్ వస్తుందా", "ఏటీఎం నుంచి డబ్బు తీయవచ్చా"],
  "OOS_OTHER_CREDIT_PRODUCTS": ["పర్సనల్ లోన్ వస్తుందా", "హోమ్ లోన్ ఇస్తారా", "కార్ లోన్ రేట్ ఎంత"],
  "OOS_INSURANCE": ["ఈ కార్డ్ పై ఇన్సూరెన్స్ ఉందా", "నాకు పాలసీ కావాలి"],
  "OOS_DISPUTE_OR_FRAUD": ["నేను ఈ లావాదేవీ చేయలేదు", "నా కార్డ్ ఎవరో వాడారు", "నా కార్డ్ పోయింది"],
  "OOS_ACCOUNT_SERVICING": ["నా అడ్రస్ మార్చాలి", "కార్డ్ బ్లాక్ చేయండి", "నా బ్యాలెన్స్ ఎంత"],
  "OOS_FOREX_AND_CHARGES": ["విదేశాల్లో ఈ కార్డ్ పనిచేస్తుందా", "ఫారెక్స్ చార్జ్ ఎంత", "లేట్ పేమెంట్ చార్జ్ ఎంత"],
  "OOS_COMPLAINT_OR_LEGAL": ["నేను ఫిర్యాదు చేయాలి", "నేను చట్టపరమైన చర్య తీసుకుంటాను", "మీ మేనేజర్ తో మాట్లాడాలి"],
  "OOS_FINANCIAL_ADVICE": ["నేను తీసుకోవాలా వద్దా", "మీరైతే ఏం చేసేవారు", "ఇది నాకు మంచిదేనా"],
  "OOS_PII_SOLICITATION": ["నా కార్డ్ నంబర్", "ఓటీపీ చెప్తాను", "నా పిన్"],
  "OOS_REWARDS": ["నా రివార్డ్ పాయింట్లు ఎన్ని", "పాయింట్లు ఎలా వాడాలి"],
  "OOS_SMALL_TALK": ["మీ పేరు ఏంటి", "మీరు ఎక్కడి నుంచి"],
 },
 "kn": {
  "OOS_CASH_ADVANCE": ["ಕ್ಯಾಶ್ ತೆಗೆದರೆ ಎಷ್ಟು ಬಡ್ಡಿ", "ಈ ಕಾರ್ಡ್ ಮೇಲೆ ಕ್ಯಾಶ್ ಸಿಗುತ್ತಾ", "ಎಟಿಎಂ ನಿಂದ ಹಣ ತೆಗೆಯಬಹುದಾ"],
  "OOS_OTHER_CREDIT_PRODUCTS": ["ಪರ್ಸನಲ್ ಲೋನ್ ಸಿಗುತ್ತಾ", "ಹೋಮ್ ಲೋನ್ ಕೊಡ್ತೀರಾ", "ಕಾರ್ ಲೋನ್ ರೇಟ್ ಎಷ್ಟು"],
  "OOS_INSURANCE": ["ಈ ಕಾರ್ಡ್ ಮೇಲೆ ಇನ್ಶೂರೆನ್ಸ್ ಇದೆಯಾ", "ನನಗೆ ಪಾಲಿಸಿ ಬೇಕು"],
  "OOS_DISPUTE_OR_FRAUD": ["ನಾನು ಈ ವ್ಯವಹಾರ ಮಾಡಿಲ್ಲ", "ನನ್ನ ಕಾರ್ಡ್ ಯಾರೋ ಬಳಸಿದ್ದಾರೆ", "ನನ್ನ ಕಾರ್ಡ್ ಕಳೆದುಹೋಗಿದೆ"],
  "OOS_ACCOUNT_SERVICING": ["ನನ್ನ ವಿಳಾಸ ಬದಲಾಯಿಸಬೇಕು", "ಕಾರ್ಡ್ ಬ್ಲಾಕ್ ಮಾಡಿ", "ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು"],
  "OOS_FOREX_AND_CHARGES": ["ವಿದೇಶದಲ್ಲಿ ಈ ಕಾರ್ಡ್ ಕೆಲಸ ಮಾಡುತ್ತಾ", "ಫಾರೆಕ್ಸ್ ಚಾರ್ಜ್ ಎಷ್ಟು", "ಲೇಟ್ ಪೇಮೆಂಟ್ ಚಾರ್ಜ್ ಎಷ್ಟು"],
  "OOS_COMPLAINT_OR_LEGAL": ["ನಾನು ದೂರು ಕೊಡಬೇಕು", "ನಾನು ಕಾನೂನು ಕ್ರಮ ತೆಗೆದುಕೊಳ್ಳುತ್ತೇನೆ", "ನಿಮ್ಮ ಮ್ಯಾನೇಜರ್ ಜೊತೆ ಮಾತಾಡಬೇಕು"],
  "OOS_FINANCIAL_ADVICE": ["ನಾನು ತೆಗೆದುಕೊಳ್ಳಲಾ ಬೇಡವಾ", "ನೀವಾಗಿದ್ದರೆ ಏನು ಮಾಡುತ್ತಿದ್ದಿರಿ", "ಇದು ನನಗೆ ಒಳ್ಳೆಯದಾ"],
  "OOS_PII_SOLICITATION": ["ನನ್ನ ಕಾರ್ಡ್ ನಂಬರ್", "ಓಟಿಪಿ ಹೇಳ್ತೇನೆ", "ನನ್ನ ಪಿನ್"],
  "OOS_REWARDS": ["ನನ್ನ ರಿವಾರ್ಡ್ ಪಾಯಿಂಟ್ ಎಷ್ಟು", "ಪಾಯಿಂಟ್ ಹೇಗೆ ಬಳಸೋದು"],
  "OOS_SMALL_TALK": ["ನಿಮ್ಮ ಹೆಸರೇನು", "ನೀವು ಎಲ್ಲಿಂದ"],
 },
 "ml": {
  "OOS_CASH_ADVANCE": ["ക്യാഷ് എടുത്താൽ എത്ര പലിശ", "ഈ കാർഡിൽ ക്യാഷ് കിട്ടുമോ", "എടിഎമ്മിൽ നിന്ന് പണം എടുക്കാമോ"],
  "OOS_OTHER_CREDIT_PRODUCTS": ["പേഴ്സണൽ ലോൺ കിട്ടുമോ", "ഹോം ലോൺ തരുമോ", "കാർ ലോൺ റേറ്റ് എത്ര"],
  "OOS_INSURANCE": ["ഈ കാർഡിൽ ഇൻഷുറൻസ് ഉണ്ടോ", "എനിക്ക് പോളിസി വേണം"],
  "OOS_DISPUTE_OR_FRAUD": ["ഞാൻ ഈ ഇടപാട് നടത്തിയിട്ടില്ല", "എന്റെ കാർഡ് ആരോ ഉപയോഗിച്ചു", "എന്റെ കാർഡ് നഷ്ടപ്പെട്ടു"],
  "OOS_ACCOUNT_SERVICING": ["എന്റെ വിലാസം മാറ്റണം", "കാർഡ് ബ്ലോക്ക് ചെയ്യൂ", "എന്റെ ബാലൻസ് എത്ര"],
  "OOS_FOREX_AND_CHARGES": ["വിദേശത്ത് ഈ കാർഡ് പ്രവർത്തിക്കുമോ", "ഫോറെക്സ് ചാർജ് എത്ര", "ലേറ്റ് പേയ്മെന്റ് ചാർജ് എത്ര"],
  "OOS_COMPLAINT_OR_LEGAL": ["എനിക്ക് പരാതി നൽകണം", "ഞാൻ നിയമനടപടി എടുക്കും", "നിങ്ങളുടെ മാനേജരോട് സംസാരിക്കണം"],
  "OOS_FINANCIAL_ADVICE": ["ഞാൻ എടുക്കണോ വേണ്ടയോ", "നിങ്ങളായിരുന്നെങ്കിൽ എന്ത് ചെയ്യുമായിരുന്നു", "ഇത് എനിക്ക് നല്ലതാണോ"],
  "OOS_PII_SOLICITATION": ["എന്റെ കാർഡ് നമ്പർ", "ഒടിപി പറയാം", "എന്റെ പിൻ"],
  "OOS_REWARDS": ["എന്റെ റിവാർഡ് പോയിന്റ് എത്ര", "പോയിന്റ് എങ്ങനെ ഉപയോഗിക്കും"],
  "OOS_SMALL_TALK": ["നിങ്ങളുടെ പേര് എന്താണ്", "നിങ്ങൾ എവിടെ നിന്ന്"],
 },
}


def main():
    # backchannels
    bpath = ROOT / "content" / "backchannels.yaml"
    bdoc = yaml.safe_load(bpath.read_text(encoding="utf-8"))
    added_b = 0
    for locale, cats in BACKCHANNELS.items():
        for cat, tokens in cats.items():
            bdoc["tokens"].setdefault(cat, {})[locale] = tokens
            added_b += len(tokens)
    head = bpath.read_text(encoding="utf-8").split("version:")[0]
    bpath.write_text(head + yaml.safe_dump(bdoc, sort_keys=False, allow_unicode=True, width=160),
                     encoding="utf-8")

    # out of scope
    opath = ROOT / "content" / "out_of_scope.yaml"
    odoc = yaml.safe_load(opath.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in odoc["categories"]}
    added_o, missing = 0, set()
    for locale, cats in OOS.items():
        for cid, examples in cats.items():
            if cid not in by_id:
                missing.add(cid)
                continue
            by_id[cid][f"examples_{locale}"] = examples
            added_o += len(examples)
    head = opath.read_text(encoding="utf-8").split("version:")[0]
    opath.write_text(head + yaml.safe_dump(odoc, sort_keys=False, allow_unicode=True, width=160),
                     encoding="utf-8")

    if missing:
        print(f"  ! unknown categories skipped: {sorted(missing)}")
    print(f"  {added_b} backchannel tokens, {added_o} out-of-scope examples "
          f"across {len(BACKCHANNELS)} languages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
