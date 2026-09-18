#!/usr/bin/env python3
"""Spoken lines and disclosures for Tamil, Telugu, Kannada and Malayalam.

    python tools/i18n_lines_dravidian.py

Same contract as tools/i18n_lines.py: keyed by the English source, slot parity enforced, and
conversational register rather than textbook - product nouns stay English because that is how
these calls are actually conducted.

All synthetic. Replaced when SBIC supplies the BLC-approved script per language.
"""

import sys

from i18n_lines import L, apply          # reuse the applier and its slot-parity check

# ---------------------------------------------------------------------- Tamil
L["ta"] = {
 "Hello, good day.": "வணக்கம்.",
 "Am I speaking with {customer_first_name}?": "நான் {customer_first_name} அவர்களிடம் பேசுகிறேனா?",
 "I am calling about an offer available on your card. It will take about a minute.":
   "உங்கள் கார்டில் உள்ள ஒரு ஆஃபர் பற்றி கால் பண்ணுகிறேன். ஒரு நிமிடம் தான் ஆகும்.",
 "I am calling about your card limit. It will take less than a minute.":
   "உங்கள் கார்டு லிமிட் பற்றி கால் பண்ணுகிறேன். ஒரு நிமிடத்துக்கும் குறைவாக ஆகும்.",
 "I am calling about an additional card available to you. It will take about a minute.":
   "உங்களுக்கு கிடைக்கும் கூடுதல் கார்டு பற்றி கால் பண்ணுகிறேன். ஒரு நிமிடம் ஆகும்.",
 "You are eligible to convert purchases above {min_txn_amt} rupees into easy monthly instalments. On your card, up to {eligible_amount} rupees can be converted over {tenure_options}.":
   "{min_txn_amt} ரூபாய்க்கு மேல் உள்ள பர்ச்சேஸ்களை எளிய மாத தவணைகளாக மாற்றலாம். உங்கள் கார்டில் {eligible_amount} ரூபாய் வரை, {tenure_options} ல் மாற்ற முடியும்.",
 "Based on your card usage, your credit limit can be increased from {current_limit} rupees to {enhanced_limit} rupees.":
   "உங்கள் கார்டு பயன்பாட்டின் அடிப்படையில், உங்கள் கிரெடிட் லிமிட் {current_limit} ரூபாயில் இருந்து {enhanced_limit} ரூபாய் வரை உயர்த்தப்படலாம்.",
 "You are eligible for an additional {brand_name} card, the {offered_card_name}, which offers {headline_benefit}.":
   "நீங்கள் கூடுதல் {brand_name} கார்டுக்கு தகுதி பெற்றுள்ளீர்கள், {offered_card_name}, இதில் {headline_benefit} கிடைக்கும்.",
 "At a tenure of {tenure_months} months, your indicative instalment would be about {indicative_emi} rupees per month.":
   "{tenure_months} மாத தவணையில், உங்கள் மாதாந்திர தவணை தோராயமாக {indicative_emi} ரூபாய் இருக்கும்.",
 "This offer is open for {offer_valid_days} days.": "இந்த ஆஃபர் {offer_valid_days} நாட்களுக்கு உள்ளது.",
 "The card is issued subject to approval.": "கார்டு அப்ரூவலுக்கு உட்பட்டு வழங்கப்படும்.",
 "Shall I connect you to our advisor to take this forward?":
   "இதை தொடர எங்கள் அட்வைசரிடம் உங்களை இணைக்கட்டுமா?",
 "Shall I connect you to our advisor to complete this?":
   "இதை முடிக்க எங்கள் அட்வைசரிடம் உங்களை இணைக்கட்டுமா?",
 "Thank you. Please stay on the line.": "நன்றி. தயவுசெய்து லைனில் இருங்கள்.",
 "Of course. The offer is open for {offer_valid_days} days. Would you prefer that our advisor explains the details now, or should we call you back?":
   "கண்டிப்பாக. இந்த ஆஃபர் {offer_valid_days} நாட்களுக்கு உள்ளது. எங்கள் அட்வைசர் இப்போது விவரங்களை சொல்லட்டுமா, அல்லது நாங்கள் திரும்ப கால் பண்ணட்டுமா?",
 "Of course. The offer stays open for {offer_valid_days} days. Would you like our advisor to explain it now, or should we call you back?":
   "கண்டிப்பாக. இந்த ஆஃபர் {offer_valid_days} நாட்கள் இருக்கும். எங்கள் அட்வைசர் இப்போது விளக்கட்டுமா, அல்லது நாங்கள் திரும்ப கால் பண்ணட்டுமா?",
 "Of course. Would you prefer that our advisor explains the details now, or should we call you back?":
   "கண்டிப்பாக. எங்கள் அட்வைசர் இப்போது விவரங்களை சொல்லட்டுமா, அல்லது நாங்கள் திரும்ப கால் பண்ணட்டுமா?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can also verify this offer on your {brand_name} app, or by calling the number printed on the back of your card. Shall I continue?":
   "இது நியாயமான கேள்வி. நான் உங்கள் கார்டு நம்பர், பின் அல்லது ஓடிபி கேட்கவில்லை, எப்போதும் கேட்க மாட்டேன். இந்த ஆஃபரை உங்கள் {brand_name} ஆப்பில், அல்லது கார்டின் பின்புறம் உள்ள நம்பருக்கு கால் பண்ணி சரிபார்க்கலாம். நான் தொடரட்டுமா?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can verify this on your {brand_name} app, or on the number printed on the back of your card. Shall I continue?":
   "இது நியாயமான கேள்வி. நான் உங்கள் கார்டு நம்பர், பின் அல்லது ஓடிபி கேட்கவில்லை, எப்போதும் கேட்க மாட்டேன். இதை உங்கள் {brand_name} ஆப்பில், அல்லது கார்டின் பின்புறம் உள்ள நம்பரில் சரிபார்க்கலாம். நான் தொடரட்டுமா?",
 "I am calling on the number registered with your {brand_name} card account. If you would prefer not to receive such calls, I can note that right away.":
   "உங்கள் {brand_name} கார்டு அக்கவுண்டில் பதிவு செய்யப்பட்ட நம்பருக்கு கால் பண்ணுகிறேன். இதுபோன்ற கால்கள் வேண்டாம் என்றால், நான் உடனே பதிவு செய்கிறேன்.",
 "That is understandable. A higher limit does not change what you spend, and there is no charge for the increase itself. Would you still like to hear the details from our advisor?":
   "இது புரிகிறது. அதிக லிமிட் உங்கள் செலவை மாற்றாது, லிமிட் உயர்த்துவதற்கு எந்த கட்டணமும் இல்லை. இருந்தாலும் எங்கள் அட்வைசரிடம் விவரங்களை கேட்க விரும்புகிறீர்களா?",
 "Many customers do hold more than one card, and each card carries its own benefits. Would you like our advisor to explain how this one differs from your existing card?":
   "பல வாடிக்கையாளர்கள் ஒன்றுக்கு மேற்பட்ட கார்டு வைத்திருக்கிறார்கள், ஒவ்வொரு கார்டுக்கும் தனி பலன்கள் உள்ளன. இது உங்கள் தற்போதைய கார்டில் இருந்து எப்படி வேறுபடுகிறது என்று எங்கள் அட்வைசர் சொல்லட்டுமா?",
 "Certainly. We will call you back at a more convenient time.":
   "கண்டிப்பாக. வசதியான நேரத்தில் நாங்கள் திரும்ப கால் பண்ணுகிறோம்.",
 "I apologise for the inconvenience. I will update our records.":
   "சிரமத்திற்கு வருந்துகிறேன். எங்கள் ரெக்கார்டை அப்டேட் பண்ணுகிறேன்.",
 "I understand. May we call you back later today?":
   "புரிகிறது. இன்று பிறகு கால் பண்ணலாமா?",
 "That is perfectly alright. Thank you for your time, and have a good day.":
   "பரவாயில்லை. உங்கள் நேரத்திற்கு நன்றி, நல்ல நாளாக இருக்கட்டும்.",
 "Thank you. Have a good day.": "நன்றி. நல்ல நாளாக இருக்கட்டும்.",
 "I have noted your request. You will not receive further promotional calls from us. Thank you.":
   "உங்கள் கோரிக்கையை பதிவு செய்துவிட்டேன். இனி எங்களிடம் இருந்து ப்ரோமோஷனல் கால்கள் வராது. நன்றி.",
 "Thank you, and sorry for the disturbance.": "நன்றி, தொந்தரவுக்கு மன்னிக்கவும்.",
 "I am ending the call now. Thank you.": "நான் இப்போது கால் முடிக்கிறேன். நன்றி.",
 "I am unable to hear you. We will try again another time. Thank you.":
   "உங்கள் குரல் கேட்கவில்லை. வேறு நேரத்தில் முயற்சி செய்கிறோம். நன்றி.",
 "I am sorry, I could not hear you. Are you still there?":
   "மன்னிக்கவும், கேட்கவில்லை. நீங்கள் லைனில் இருக்கிறீர்களா?",
 "Certainly.": "கண்டிப்பாக.",
 "That is a good question, and I would rather our advisor answer it properly for you.":
   "இது நல்ல கேள்வி, இதற்கு எங்கள் அட்வைசர் சரியான பதில் சொல்வது நல்லது.",
 "I am {agent_display_name}, calling on behalf of {brand_name}.":
   "நான் {agent_display_name}, {brand_name} சார்பாக கால் பண்ணுகிறேன்.",
 "This call is recorded for quality and training purposes.":
   "இந்த கால் குவாலிட்டி மற்றும் ட்ரெயினிங்குக்காக ரெக்கார்ட் செய்யப்படுகிறது.",
 "This conversion carries interest of {roi_annual_pct} percent per annum and a one-time processing fee of {processing_fee} rupees. Goods and services tax applies as per government rules.":
   "இந்த கன்வர்ஷனுக்கு ஆண்டுக்கு {roi_annual_pct} சதவீதம் வட்டி மற்றும் {processing_fee} ரூபாய் ஒருமுறை ப்ராசசிங் கட்டணம் உள்ளது. ஜிஎஸ்டி அரசாங்க விதிகளின்படி பொருந்தும்.",
 "The revised limit is subject to the terms and conditions of your card agreement.":
   "திருத்தப்பட்ட லிமிட் உங்கள் கார்டு ஒப்பந்தத்தின் விதிமுறைகளுக்கு உட்பட்டது.",
 "This card carries a joining fee of {joining_fee} rupees and an annual fee of {annual_fee} rupees, which is reversed on {fee_waiver_condition}.":
   "இந்த கார்டுக்கு {joining_fee} ரூபாய் ஜாய்னிங் கட்டணம் மற்றும் {annual_fee} ரூபாய் ஆண்டு கட்டணம் உள்ளது, இது {fee_waiver_condition} ல் திரும்ப வழங்கப்படும்.",
 "I will now connect you to our advisor, who will confirm your details and complete the process.":
   "இப்போது உங்களை எங்கள் அட்வைசரிடம் இணைக்கிறேன், அவர் உங்கள் விவரங்களை உறுதி செய்து செயல்முறையை முடிப்பார்.",
}

# ---------------------------------------------------------------------- Telugu
L["te"] = {
 "Hello, good day.": "నమస్కారం.",
 "Am I speaking with {customer_first_name}?": "నేను {customer_first_name} గారితో మాట్లాడుతున్నానా?",
 "I am calling about an offer available on your card. It will take about a minute.":
   "మీ కార్డ్ పై ఉన్న ఒక ఆఫర్ గురించి కాల్ చేస్తున్నాను. ఒక నిమిషం పడుతుంది.",
 "I am calling about your card limit. It will take less than a minute.":
   "మీ కార్డ్ లిమిట్ గురించి కాల్ చేస్తున్నాను. ఒక నిమిషం కంటే తక్కువ పడుతుంది.",
 "I am calling about an additional card available to you. It will take about a minute.":
   "మీకు అందుబాటులో ఉన్న అదనపు కార్డ్ గురించి కాల్ చేస్తున్నాను. ఒక నిమిషం పడుతుంది.",
 "You are eligible to convert purchases above {min_txn_amt} rupees into easy monthly instalments. On your card, up to {eligible_amount} rupees can be converted over {tenure_options}.":
   "{min_txn_amt} రూపాయల పైన ఉన్న పర్చేజ్‌లను సులభమైన నెలవారీ వాయిదాలుగా మార్చుకోవచ్చు. మీ కార్డ్ పై {eligible_amount} రూపాయల వరకు, {tenure_options} లో మార్చవచ్చు.",
 "Based on your card usage, your credit limit can be increased from {current_limit} rupees to {enhanced_limit} rupees.":
   "మీ కార్డ్ వినియోగం ఆధారంగా, మీ క్రెడిట్ లిమిట్ {current_limit} రూపాయల నుంచి {enhanced_limit} రూపాయలకు పెరగవచ్చు.",
 "You are eligible for an additional {brand_name} card, the {offered_card_name}, which offers {headline_benefit}.":
   "మీరు అదనపు {brand_name} కార్డ్ కు అర్హులు, {offered_card_name}, ఇందులో {headline_benefit} లభిస్తుంది.",
 "At a tenure of {tenure_months} months, your indicative instalment would be about {indicative_emi} rupees per month.":
   "{tenure_months} నెలల వ్యవధిలో, మీ అంచనా వాయిదా నెలకు సుమారు {indicative_emi} రూపాయలు ఉంటుంది.",
 "This offer is open for {offer_valid_days} days.": "ఈ ఆఫర్ {offer_valid_days} రోజులు అందుబాటులో ఉంది.",
 "The card is issued subject to approval.": "కార్డ్ అప్రూవల్ కు లోబడి ఇవ్వబడుతుంది.",
 "Shall I connect you to our advisor to take this forward?":
   "దీన్ని ముందుకు తీసుకెళ్ళడానికి మిమ్మల్ని మా అడ్వైజర్ కు కనెక్ట్ చేయనా?",
 "Shall I connect you to our advisor to complete this?":
   "దీన్ని పూర్తి చేయడానికి మిమ్మల్ని మా అడ్వైజర్ కు కనెక్ట్ చేయనా?",
 "Thank you. Please stay on the line.": "ధన్యవాదాలు. దయచేసి లైన్ లో ఉండండి.",
 "Of course. The offer is open for {offer_valid_days} days. Would you prefer that our advisor explains the details now, or should we call you back?":
   "తప్పకుండా. ఈ ఆఫర్ {offer_valid_days} రోజులు ఉంది. మా అడ్వైజర్ ఇప్పుడు వివరాలు చెప్పాలా, లేక మేము తిరిగి కాల్ చేయాలా?",
 "Of course. The offer stays open for {offer_valid_days} days. Would you like our advisor to explain it now, or should we call you back?":
   "తప్పకుండా. ఈ ఆఫర్ {offer_valid_days} రోజులు ఉంటుంది. మా అడ్వైజర్ ఇప్పుడు వివరించాలా, లేక మేము తిరిగి కాల్ చేయాలా?",
 "Of course. Would you prefer that our advisor explains the details now, or should we call you back?":
   "తప్పకుండా. మా అడ్వైజర్ ఇప్పుడు వివరాలు చెప్పాలా, లేక మేము తిరిగి కాల్ చేయాలా?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can also verify this offer on your {brand_name} app, or by calling the number printed on the back of your card. Shall I continue?":
   "ఇది సరైన ప్రశ్న. నేను మీ కార్డ్ నంబర్, పిన్ లేదా ఓటీపీ అడగడం లేదు, ఎప్పుడూ అడగను. ఈ ఆఫర్ ను మీ {brand_name} యాప్ లో, లేదా కార్డ్ వెనుక ఉన్న నంబర్ కు కాల్ చేసి చెక్ చేసుకోవచ్చు. నేను కొనసాగించనా?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can verify this on your {brand_name} app, or on the number printed on the back of your card. Shall I continue?":
   "ఇది సరైన ప్రశ్న. నేను మీ కార్డ్ నంబర్, పిన్ లేదా ఓటీపీ అడగడం లేదు, ఎప్పుడూ అడగను. దీన్ని మీ {brand_name} యాప్ లో, లేదా కార్డ్ వెనుక ఉన్న నంబర్ లో చెక్ చేసుకోవచ్చు. నేను కొనసాగించనా?",
 "I am calling on the number registered with your {brand_name} card account. If you would prefer not to receive such calls, I can note that right away.":
   "మీ {brand_name} కార్డ్ ఖాతాలో రిజిస్టర్ అయిన నంబర్ కు కాల్ చేస్తున్నాను. మీకు ఇలాంటి కాల్స్ వద్దు అనుకుంటే, నేను వెంటనే నోట్ చేస్తాను.",
 "That is understandable. A higher limit does not change what you spend, and there is no charge for the increase itself. Would you still like to hear the details from our advisor?":
   "ఇది అర్థం చేసుకోగలను. ఎక్కువ లిమిట్ వల్ల మీ ఖర్చు పెరగదు, లిమిట్ పెంచడానికి ఎలాంటి చార్జ్ లేదు. అయినా మా అడ్వైజర్ నుంచి వివరాలు వినాలనుకుంటున్నారా?",
 "Many customers do hold more than one card, and each card carries its own benefits. Would you like our advisor to explain how this one differs from your existing card?":
   "చాలా మంది కస్టమర్లు ఒకటి కంటే ఎక్కువ కార్డులు కలిగి ఉంటారు, ప్రతి కార్డ్ కు దాని స్వంత ప్రయోజనాలు ఉంటాయి. ఇది మీ ప్రస్తుత కార్డ్ నుంచి ఎలా వేరుగా ఉందో మా అడ్వైజర్ వివరించాలా?",
 "Certainly. We will call you back at a more convenient time.":
   "తప్పకుండా. మేము మీకు అనుకూలమైన సమయంలో తిరిగి కాల్ చేస్తాము.",
 "I apologise for the inconvenience. I will update our records.":
   "అసౌకర్యానికి క్షమించండి. మా రికార్డులను అప్‌డేట్ చేస్తాను.",
 "I understand. May we call you back later today?":
   "అర్థమైంది. ఈరోజు తర్వాత కాల్ చేయవచ్చా?",
 "That is perfectly alright. Thank you for your time, and have a good day.":
   "ఫర్వాలేదు. మీ సమయానికి ధన్యవాదాలు, మీ రోజు బాగుండాలి.",
 "Thank you. Have a good day.": "ధన్యవాదాలు. మీ రోజు బాగుండాలి.",
 "I have noted your request. You will not receive further promotional calls from us. Thank you.":
   "మీ అభ్యర్థనను నోట్ చేశాను. ఇకపై మా నుంచి ప్రమోషనల్ కాల్స్ రావు. ధన్యవాదాలు.",
 "Thank you, and sorry for the disturbance.": "ధన్యవాదాలు, ఇబ్బందికి క్షమించండి.",
 "I am ending the call now. Thank you.": "నేను ఇప్పుడు కాల్ ముగిస్తున్నాను. ధన్యవాదాలు.",
 "I am unable to hear you. We will try again another time. Thank you.":
   "మీ మాట వినిపించడం లేదు. మరో సమయంలో ప్రయత్నిస్తాము. ధన్యవాదాలు.",
 "I am sorry, I could not hear you. Are you still there?":
   "క్షమించండి, వినిపించలేదు. మీరు లైన్ లో ఉన్నారా?",
 "Certainly.": "తప్పకుండా.",
 "That is a good question, and I would rather our advisor answer it properly for you.":
   "ఇది మంచి ప్రశ్న, దీనికి మా అడ్వైజర్ సరైన సమాధానం ఇవ్వడం మంచిది.",
 "I am {agent_display_name}, calling on behalf of {brand_name}.":
   "నేను {agent_display_name}, {brand_name} తరపున కాల్ చేస్తున్నాను.",
 "This call is recorded for quality and training purposes.":
   "ఈ కాల్ క్వాలిటీ మరియు ట్రైనింగ్ కోసం రికార్డ్ చేయబడుతోంది.",
 "This conversion carries interest of {roi_annual_pct} percent per annum and a one-time processing fee of {processing_fee} rupees. Goods and services tax applies as per government rules.":
   "ఈ కన్వర్షన్ పై సంవత్సరానికి {roi_annual_pct} శాతం వడ్డీ మరియు {processing_fee} రూపాయల ఒకసారి ప్రాసెసింగ్ ఫీజు ఉంటుంది. జీఎస్టీ ప్రభుత్వ నిబంధనల ప్రకారం వర్తిస్తుంది.",
 "The revised limit is subject to the terms and conditions of your card agreement.":
   "సవరించిన లిమిట్ మీ కార్డ్ ఒప్పందం నిబంధనలకు లోబడి ఉంటుంది.",
 "This card carries a joining fee of {joining_fee} rupees and an annual fee of {annual_fee} rupees, which is reversed on {fee_waiver_condition}.":
   "ఈ కార్డ్ పై {joining_fee} రూపాయల జాయినింగ్ ఫీజు మరియు {annual_fee} రూపాయల వార్షిక ఫీజు ఉంటుంది, ఇది {fee_waiver_condition} పై తిరిగి ఇవ్వబడుతుంది.",
 "I will now connect you to our advisor, who will confirm your details and complete the process.":
   "ఇప్పుడు మిమ్మల్ని మా అడ్వైజర్ కు కనెక్ట్ చేస్తున్నాను, వారు మీ వివరాలు నిర్ధారించి ప్రక్రియను పూర్తి చేస్తారు.",
}

# ---------------------------------------------------------------------- Kannada
L["kn"] = {
 "Hello, good day.": "ನಮಸ್ಕಾರ.",
 "Am I speaking with {customer_first_name}?": "ನಾನು {customer_first_name} ಅವರೊಂದಿಗೆ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆಯೇ?",
 "I am calling about an offer available on your card. It will take about a minute.":
   "ನಿಮ್ಮ ಕಾರ್ಡ್ ಮೇಲಿನ ಒಂದು ಆಫರ್ ಬಗ್ಗೆ ಕಾಲ್ ಮಾಡುತ್ತಿದ್ದೇನೆ. ಸುಮಾರು ಒಂದು ನಿಮಿಷ ಆಗುತ್ತದೆ.",
 "I am calling about your card limit. It will take less than a minute.":
   "ನಿಮ್ಮ ಕಾರ್ಡ್ ಲಿಮಿಟ್ ಬಗ್ಗೆ ಕಾಲ್ ಮಾಡುತ್ತಿದ್ದೇನೆ. ಒಂದು ನಿಮಿಷಕ್ಕಿಂತ ಕಡಿಮೆ ಆಗುತ್ತದೆ.",
 "I am calling about an additional card available to you. It will take about a minute.":
   "ನಿಮಗೆ ಲಭ್ಯವಿರುವ ಹೆಚ್ಚುವರಿ ಕಾರ್ಡ್ ಬಗ್ಗೆ ಕಾಲ್ ಮಾಡುತ್ತಿದ್ದೇನೆ. ಸುಮಾರು ಒಂದು ನಿಮಿಷ ಆಗುತ್ತದೆ.",
 "You are eligible to convert purchases above {min_txn_amt} rupees into easy monthly instalments. On your card, up to {eligible_amount} rupees can be converted over {tenure_options}.":
   "{min_txn_amt} ರೂಪಾಯಿಗಿಂತ ಹೆಚ್ಚಿನ ಖರೀದಿಗಳನ್ನು ಸುಲಭ ಮಾಸಿಕ ಕಂತುಗಳಾಗಿ ಬದಲಾಯಿಸಬಹುದು. ನಿಮ್ಮ ಕಾರ್ಡ್ ಮೇಲೆ {eligible_amount} ರೂಪಾಯಿವರೆಗೆ, {tenure_options} ನಲ್ಲಿ ಬದಲಾಯಿಸಬಹುದು.",
 "Based on your card usage, your credit limit can be increased from {current_limit} rupees to {enhanced_limit} rupees.":
   "ನಿಮ್ಮ ಕಾರ್ಡ್ ಬಳಕೆಯ ಆಧಾರದ ಮೇಲೆ, ನಿಮ್ಮ ಕ್ರೆಡಿಟ್ ಲಿಮಿಟ್ {current_limit} ರೂಪಾಯಿಯಿಂದ {enhanced_limit} ರೂಪಾಯಿಗೆ ಹೆಚ್ಚಾಗಬಹುದು.",
 "You are eligible for an additional {brand_name} card, the {offered_card_name}, which offers {headline_benefit}.":
   "ನೀವು ಹೆಚ್ಚುವರಿ {brand_name} ಕಾರ್ಡ್ ಗೆ ಅರ್ಹರಾಗಿದ್ದೀರಿ, {offered_card_name}, ಇದರಲ್ಲಿ {headline_benefit} ಸಿಗುತ್ತದೆ.",
 "At a tenure of {tenure_months} months, your indicative instalment would be about {indicative_emi} rupees per month.":
   "{tenure_months} ತಿಂಗಳ ಅವಧಿಯಲ್ಲಿ, ನಿಮ್ಮ ಅಂದಾಜು ಕಂತು ತಿಂಗಳಿಗೆ ಸುಮಾರು {indicative_emi} ರೂಪಾಯಿ ಆಗುತ್ತದೆ.",
 "This offer is open for {offer_valid_days} days.": "ಈ ಆಫರ್ {offer_valid_days} ದಿನಗಳವರೆಗೆ ಲಭ್ಯವಿದೆ.",
 "The card is issued subject to approval.": "ಕಾರ್ಡ್ ಅನುಮೋದನೆಗೆ ಒಳಪಟ್ಟು ನೀಡಲಾಗುತ್ತದೆ.",
 "Shall I connect you to our advisor to take this forward?":
   "ಇದನ್ನು ಮುಂದುವರಿಸಲು ನಿಮ್ಮನ್ನು ನಮ್ಮ ಅಡ್ವೈಸರ್ ಗೆ ಕನೆಕ್ಟ್ ಮಾಡಲೇ?",
 "Shall I connect you to our advisor to complete this?":
   "ಇದನ್ನು ಪೂರ್ಣಗೊಳಿಸಲು ನಿಮ್ಮನ್ನು ನಮ್ಮ ಅಡ್ವೈಸರ್ ಗೆ ಕನೆಕ್ಟ್ ಮಾಡಲೇ?",
 "Thank you. Please stay on the line.": "ಧನ್ಯವಾದಗಳು. ದಯವಿಟ್ಟು ಲೈನ್ ನಲ್ಲಿ ಇರಿ.",
 "Of course. The offer is open for {offer_valid_days} days. Would you prefer that our advisor explains the details now, or should we call you back?":
   "ಖಂಡಿತ. ಈ ಆಫರ್ {offer_valid_days} ದಿನ ಇದೆ. ನಮ್ಮ ಅಡ್ವೈಸರ್ ಈಗ ವಿವರ ಹೇಳಲೇ, ಅಥವಾ ನಾವು ಮತ್ತೆ ಕಾಲ್ ಮಾಡಲೇ?",
 "Of course. The offer stays open for {offer_valid_days} days. Would you like our advisor to explain it now, or should we call you back?":
   "ಖಂಡಿತ. ಈ ಆಫರ್ {offer_valid_days} ದಿನ ಇರುತ್ತದೆ. ನಮ್ಮ ಅಡ್ವೈಸರ್ ಈಗ ವಿವರಿಸಲೇ, ಅಥವಾ ನಾವು ಮತ್ತೆ ಕಾಲ್ ಮಾಡಲೇ?",
 "Of course. Would you prefer that our advisor explains the details now, or should we call you back?":
   "ಖಂಡಿತ. ನಮ್ಮ ಅಡ್ವೈಸರ್ ಈಗ ವಿವರ ಹೇಳಲೇ, ಅಥವಾ ನಾವು ಮತ್ತೆ ಕಾಲ್ ಮಾಡಲೇ?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can also verify this offer on your {brand_name} app, or by calling the number printed on the back of your card. Shall I continue?":
   "ಇದು ಸರಿಯಾದ ಪ್ರಶ್ನೆ. ನಾನು ನಿಮ್ಮ ಕಾರ್ಡ್ ನಂಬರ್, ಪಿನ್ ಅಥವಾ ಓಟಿಪಿ ಕೇಳುತ್ತಿಲ್ಲ, ಎಂದಿಗೂ ಕೇಳುವುದಿಲ್ಲ. ಈ ಆಫರ್ ಅನ್ನು ನಿಮ್ಮ {brand_name} ಆ್ಯಪ್ ನಲ್ಲಿ, ಅಥವಾ ಕಾರ್ಡ್ ಹಿಂದೆ ಇರುವ ನಂಬರ್ ಗೆ ಕಾಲ್ ಮಾಡಿ ಪರಿಶೀಲಿಸಬಹುದು. ನಾನು ಮುಂದುವರಿಸಲೇ?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can verify this on your {brand_name} app, or on the number printed on the back of your card. Shall I continue?":
   "ಇದು ಸರಿಯಾದ ಪ್ರಶ್ನೆ. ನಾನು ನಿಮ್ಮ ಕಾರ್ಡ್ ನಂಬರ್, ಪಿನ್ ಅಥವಾ ಓಟಿಪಿ ಕೇಳುತ್ತಿಲ್ಲ, ಎಂದಿಗೂ ಕೇಳುವುದಿಲ್ಲ. ಇದನ್ನು ನಿಮ್ಮ {brand_name} ಆ್ಯಪ್ ನಲ್ಲಿ, ಅಥವಾ ಕಾರ್ಡ್ ಹಿಂದೆ ಇರುವ ನಂಬರ್ ನಲ್ಲಿ ಪರಿಶೀಲಿಸಬಹುದು. ನಾನು ಮುಂದುವರಿಸಲೇ?",
 "I am calling on the number registered with your {brand_name} card account. If you would prefer not to receive such calls, I can note that right away.":
   "ನಿಮ್ಮ {brand_name} ಕಾರ್ಡ್ ಖಾತೆಯಲ್ಲಿ ನೋಂದಾಯಿತ ನಂಬರ್ ಗೆ ಕಾಲ್ ಮಾಡುತ್ತಿದ್ದೇನೆ. ನಿಮಗೆ ಇಂತಹ ಕಾಲ್ ಬೇಡ ಎಂದಾದರೆ, ನಾನು ಈಗಲೇ ನೋಂದಾಯಿಸುತ್ತೇನೆ.",
 "That is understandable. A higher limit does not change what you spend, and there is no charge for the increase itself. Would you still like to hear the details from our advisor?":
   "ಇದು ಅರ್ಥವಾಗುತ್ತದೆ. ಹೆಚ್ಚಿನ ಲಿಮಿಟ್ ನಿಮ್ಮ ಖರ್ಚನ್ನು ಬದಲಾಯಿಸುವುದಿಲ್ಲ, ಲಿಮಿಟ್ ಹೆಚ್ಚಿಸಲು ಯಾವುದೇ ಶುಲ್ಕವಿಲ್ಲ. ಆದರೂ ನಮ್ಮ ಅಡ್ವೈಸರ್ ಇಂದ ವಿವರ ಕೇಳಲು ಬಯಸುತ್ತೀರಾ?",
 "Many customers do hold more than one card, and each card carries its own benefits. Would you like our advisor to explain how this one differs from your existing card?":
   "ಅನೇಕ ಗ್ರಾಹಕರು ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಕಾರ್ಡ್ ಹೊಂದಿರುತ್ತಾರೆ, ಪ್ರತಿ ಕಾರ್ಡ್ ಗೂ ತನ್ನದೇ ಪ್ರಯೋಜನಗಳಿವೆ. ಇದು ನಿಮ್ಮ ಈಗಿನ ಕಾರ್ಡ್ ಗಿಂತ ಹೇಗೆ ಭಿನ್ನ ಎಂದು ನಮ್ಮ ಅಡ್ವೈಸರ್ ವಿವರಿಸಲೇ?",
 "Certainly. We will call you back at a more convenient time.":
   "ಖಂಡಿತ. ನಾವು ನಿಮಗೆ ಅನುಕೂಲಕರ ಸಮಯದಲ್ಲಿ ಮತ್ತೆ ಕಾಲ್ ಮಾಡುತ್ತೇವೆ.",
 "I apologise for the inconvenience. I will update our records.":
   "ಅನಾನುಕೂಲತೆಗೆ ಕ್ಷಮಿಸಿ. ನಾನು ನಮ್ಮ ದಾಖಲೆಗಳನ್ನು ಅಪ್‌ಡೇಟ್ ಮಾಡುತ್ತೇನೆ.",
 "I understand. May we call you back later today?":
   "ಅರ್ಥವಾಯಿತು. ಇಂದು ನಂತರ ಕಾಲ್ ಮಾಡಬಹುದೇ?",
 "That is perfectly alright. Thank you for your time, and have a good day.":
   "ಪರವಾಗಿಲ್ಲ. ನಿಮ್ಮ ಸಮಯಕ್ಕೆ ಧನ್ಯವಾದಗಳು, ನಿಮ್ಮ ದಿನ ಚೆನ್ನಾಗಿರಲಿ.",
 "Thank you. Have a good day.": "ಧನ್ಯವಾದಗಳು. ನಿಮ್ಮ ದಿನ ಚೆನ್ನಾಗಿರಲಿ.",
 "I have noted your request. You will not receive further promotional calls from us. Thank you.":
   "ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ದಾಖಲಿಸಿದ್ದೇನೆ. ಇನ್ನು ಮುಂದೆ ನಮ್ಮಿಂದ ಪ್ರಚಾರದ ಕಾಲ್ ಬರುವುದಿಲ್ಲ. ಧನ್ಯವಾದಗಳು.",
 "Thank you, and sorry for the disturbance.": "ಧನ್ಯವಾದಗಳು, ತೊಂದರೆಗೆ ಕ್ಷಮಿಸಿ.",
 "I am ending the call now. Thank you.": "ನಾನು ಈಗ ಕಾಲ್ ಮುಗಿಸುತ್ತಿದ್ದೇನೆ. ಧನ್ಯವಾದಗಳು.",
 "I am unable to hear you. We will try again another time. Thank you.":
   "ನಿಮ್ಮ ಧ್ವನಿ ಕೇಳಿಸುತ್ತಿಲ್ಲ. ನಾವು ಇನ್ನೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸುತ್ತೇವೆ. ಧನ್ಯವಾದಗಳು.",
 "I am sorry, I could not hear you. Are you still there?":
   "ಕ್ಷಮಿಸಿ, ಕೇಳಿಸಲಿಲ್ಲ. ನೀವು ಲೈನ್ ನಲ್ಲಿ ಇದ್ದೀರಾ?",
 "Certainly.": "ಖಂಡಿತ.",
 "That is a good question, and I would rather our advisor answer it properly for you.":
   "ಇದು ಒಳ್ಳೆಯ ಪ್ರಶ್ನೆ, ಇದಕ್ಕೆ ನಮ್ಮ ಅಡ್ವೈಸರ್ ಸರಿಯಾದ ಉತ್ತರ ಕೊಡುವುದು ಒಳ್ಳೆಯದು.",
 "I am {agent_display_name}, calling on behalf of {brand_name}.":
   "ನಾನು {agent_display_name}, {brand_name} ಪರವಾಗಿ ಕಾಲ್ ಮಾಡುತ್ತಿದ್ದೇನೆ.",
 "This call is recorded for quality and training purposes.":
   "ಈ ಕಾಲ್ ಕ್ವಾಲಿಟಿ ಮತ್ತು ಟ್ರೈನಿಂಗ್ ಗಾಗಿ ರೆಕಾರ್ಡ್ ಆಗುತ್ತಿದೆ.",
 "This conversion carries interest of {roi_annual_pct} percent per annum and a one-time processing fee of {processing_fee} rupees. Goods and services tax applies as per government rules.":
   "ಈ ಕನ್ವರ್ಶನ್ ಮೇಲೆ ವಾರ್ಷಿಕ {roi_annual_pct} ಶೇಕಡಾ ಬಡ್ಡಿ ಮತ್ತು {processing_fee} ರೂಪಾಯಿ ಒಂದು ಬಾರಿಯ ಪ್ರೊಸೆಸಿಂಗ್ ಶುಲ್ಕ ಇರುತ್ತದೆ. ಜಿಎಸ್‌ಟಿ ಸರ್ಕಾರಿ ನಿಯಮಗಳ ಪ್ರಕಾರ ಅನ್ವಯಿಸುತ್ತದೆ.",
 "The revised limit is subject to the terms and conditions of your card agreement.":
   "ಪರಿಷ್ಕೃತ ಲಿಮಿಟ್ ನಿಮ್ಮ ಕಾರ್ಡ್ ಒಪ್ಪಂದದ ನಿಯಮಗಳಿಗೆ ಒಳಪಟ್ಟಿದೆ.",
 "This card carries a joining fee of {joining_fee} rupees and an annual fee of {annual_fee} rupees, which is reversed on {fee_waiver_condition}.":
   "ಈ ಕಾರ್ಡ್ ಗೆ {joining_fee} ರೂಪಾಯಿ ಜಾಯಿನಿಂಗ್ ಶುಲ್ಕ ಮತ್ತು {annual_fee} ರೂಪಾಯಿ ವಾರ್ಷಿಕ ಶುಲ್ಕ ಇದೆ, ಇದು {fee_waiver_condition} ಮೇಲೆ ಹಿಂತಿರುಗಿಸಲಾಗುತ್ತದೆ.",
 "I will now connect you to our advisor, who will confirm your details and complete the process.":
   "ಈಗ ನಿಮ್ಮನ್ನು ನಮ್ಮ ಅಡ್ವೈಸರ್ ಗೆ ಕನೆಕ್ಟ್ ಮಾಡುತ್ತಿದ್ದೇನೆ, ಅವರು ನಿಮ್ಮ ವಿವರಗಳನ್ನು ಖಚಿತಪಡಿಸಿ ಪ್ರಕ್ರಿಯೆ ಪೂರ್ಣಗೊಳಿಸುತ್ತಾರೆ.",
}

# ---------------------------------------------------------------------- Malayalam
L["ml"] = {
 "Hello, good day.": "നമസ്കാരം.",
 "Am I speaking with {customer_first_name}?": "ഞാൻ {customer_first_name} യോടാണോ സംസാരിക്കുന്നത്?",
 "I am calling about an offer available on your card. It will take about a minute.":
   "നിങ്ങളുടെ കാർഡിലുള്ള ഒരു ഓഫറിനെക്കുറിച്ച് വിളിക്കുന്നു. ഏകദേശം ഒരു മിനിറ്റ് എടുക്കും.",
 "I am calling about your card limit. It will take less than a minute.":
   "നിങ്ങളുടെ കാർഡ് ലിമിറ്റിനെക്കുറിച്ച് വിളിക്കുന്നു. ഒരു മിനിറ്റിൽ താഴെ എടുക്കും.",
 "I am calling about an additional card available to you. It will take about a minute.":
   "നിങ്ങൾക്ക് ലഭ്യമായ ഒരു അധിക കാർഡിനെക്കുറിച്ച് വിളിക്കുന്നു. ഏകദേശം ഒരു മിനിറ്റ് എടുക്കും.",
 "You are eligible to convert purchases above {min_txn_amt} rupees into easy monthly instalments. On your card, up to {eligible_amount} rupees can be converted over {tenure_options}.":
   "{min_txn_amt} രൂപയ്ക്ക് മുകളിലുള്ള പർച്ചേസുകൾ എളുപ്പമുള്ള മാസ തവണകളാക്കി മാറ്റാം. നിങ്ങളുടെ കാർഡിൽ {eligible_amount} രൂപ വരെ, {tenure_options} ൽ മാറ്റാൻ കഴിയും.",
 "Based on your card usage, your credit limit can be increased from {current_limit} rupees to {enhanced_limit} rupees.":
   "നിങ്ങളുടെ കാർഡ് ഉപയോഗത്തിന്റെ അടിസ്ഥാനത്തിൽ, നിങ്ങളുടെ ക്രെഡിറ്റ് ലിമിറ്റ് {current_limit} രൂപയിൽ നിന്ന് {enhanced_limit} രൂപയായി വർദ്ധിപ്പിക്കാം.",
 "You are eligible for an additional {brand_name} card, the {offered_card_name}, which offers {headline_benefit}.":
   "നിങ്ങൾക്ക് ഒരു അധിക {brand_name} കാർഡിന് അർഹതയുണ്ട്, {offered_card_name}, അതിൽ {headline_benefit} ലഭിക്കും.",
 "At a tenure of {tenure_months} months, your indicative instalment would be about {indicative_emi} rupees per month.":
   "{tenure_months} മാസത്തെ കാലാവധിയിൽ, നിങ്ങളുടെ ഏകദേശ തവണ മാസം {indicative_emi} രൂപ ആയിരിക്കും.",
 "This offer is open for {offer_valid_days} days.": "ഈ ഓഫർ {offer_valid_days} ദിവസത്തേക്ക് ലഭ്യമാണ്.",
 "The card is issued subject to approval.": "കാർഡ് അംഗീകാരത്തിന് വിധേയമായി നൽകുന്നു.",
 "Shall I connect you to our advisor to take this forward?":
   "ഇത് മുന്നോട്ട് കൊണ്ടുപോകാൻ ഞാൻ നിങ്ങളെ ഞങ്ങളുടെ അഡ്വൈസറുമായി ബന്ധിപ്പിക്കട്ടെ?",
 "Shall I connect you to our advisor to complete this?":
   "ഇത് പൂർത്തിയാക്കാൻ ഞാൻ നിങ്ങളെ ഞങ്ങളുടെ അഡ്വൈസറുമായി ബന്ധിപ്പിക്കട്ടെ?",
 "Thank you. Please stay on the line.": "നന്ദി. ദയവായി ലൈനിൽ തുടരുക.",
 "Of course. The offer is open for {offer_valid_days} days. Would you prefer that our advisor explains the details now, or should we call you back?":
   "തീർച്ചയായും. ഈ ഓഫർ {offer_valid_days} ദിവസം ലഭ്യമാണ്. ഞങ്ങളുടെ അഡ്വൈസർ ഇപ്പോൾ വിശദാംശങ്ങൾ പറയണോ, അതോ ഞങ്ങൾ തിരികെ വിളിക്കണോ?",
 "Of course. The offer stays open for {offer_valid_days} days. Would you like our advisor to explain it now, or should we call you back?":
   "തീർച്ചയായും. ഈ ഓഫർ {offer_valid_days} ദിവസം ഉണ്ടാകും. ഞങ്ങളുടെ അഡ്വൈസർ ഇപ്പോൾ വിശദീകരിക്കണോ, അതോ ഞങ്ങൾ തിരികെ വിളിക്കണോ?",
 "Of course. Would you prefer that our advisor explains the details now, or should we call you back?":
   "തീർച്ചയായും. ഞങ്ങളുടെ അഡ്വൈസർ ഇപ്പോൾ വിശദാംശങ്ങൾ പറയണോ, അതോ ഞങ്ങൾ തിരികെ വിളിക്കണോ?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can also verify this offer on your {brand_name} app, or by calling the number printed on the back of your card. Shall I continue?":
   "ഇത് ന്യായമായ ചോദ്യമാണ്. ഞാൻ നിങ്ങളുടെ കാർഡ് നമ്പർ, പിൻ അല്ലെങ്കിൽ ഒടിപി ചോദിക്കുന്നില്ല, ഒരിക്കലും ചോദിക്കില്ല. ഈ ഓഫർ നിങ്ങളുടെ {brand_name} ആപ്പിൽ, അല്ലെങ്കിൽ കാർഡിന്റെ പിന്നിൽ അച്ചടിച്ച നമ്പറിൽ വിളിച്ച് പരിശോധിക്കാം. ഞാൻ തുടരട്ടെ?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can verify this on your {brand_name} app, or on the number printed on the back of your card. Shall I continue?":
   "ഇത് ന്യായമായ ചോദ്യമാണ്. ഞാൻ നിങ്ങളുടെ കാർഡ് നമ്പർ, പിൻ അല്ലെങ്കിൽ ഒടിപി ചോദിക്കുന്നില്ല, ഒരിക്കലും ചോദിക്കില്ല. ഇത് നിങ്ങളുടെ {brand_name} ആപ്പിൽ, അല്ലെങ്കിൽ കാർഡിന്റെ പിന്നിൽ അച്ചടിച്ച നമ്പറിൽ പരിശോധിക്കാം. ഞാൻ തുടരട്ടെ?",
 "I am calling on the number registered with your {brand_name} card account. If you would prefer not to receive such calls, I can note that right away.":
   "നിങ്ങളുടെ {brand_name} കാർഡ് അക്കൗണ്ടിൽ രജിസ്റ്റർ ചെയ്ത നമ്പറിലാണ് വിളിക്കുന്നത്. ഇത്തരം കോളുകൾ വേണ്ടെങ്കിൽ, ഞാൻ ഉടൻ രേഖപ്പെടുത്താം.",
 "That is understandable. A higher limit does not change what you spend, and there is no charge for the increase itself. Would you still like to hear the details from our advisor?":
   "ഇത് മനസ്സിലാക്കാം. കൂടുതൽ ലിമിറ്റ് നിങ്ങളുടെ ചെലവ് മാറ്റുന്നില്ല, ലിമിറ്റ് കൂട്ടുന്നതിന് ചാർജ് ഇല്ല. എന്നാലും ഞങ്ങളുടെ അഡ്വൈസറിൽ നിന്ന് വിശദാംശങ്ങൾ കേൾക്കാൻ താല്പര്യമുണ്ടോ?",
 "Many customers do hold more than one card, and each card carries its own benefits. Would you like our advisor to explain how this one differs from your existing card?":
   "പല ഉപഭോക്താക്കളും ഒന്നിലധികം കാർഡ് കൈവശം വയ്ക്കുന്നു, ഓരോ കാർഡിനും അതിന്റേതായ ആനുകൂല്യങ്ങളുണ്ട്. ഇത് നിങ്ങളുടെ നിലവിലെ കാർഡിൽ നിന്ന് എങ്ങനെ വ്യത്യാസപ്പെട്ടിരിക്കുന്നു എന്ന് ഞങ്ങളുടെ അഡ്വൈസർ വിശദീകരിക്കണോ?",
 "Certainly. We will call you back at a more convenient time.":
   "തീർച്ചയായും. സൗകര്യപ്രദമായ സമയത്ത് ഞങ്ങൾ തിരികെ വിളിക്കാം.",
 "I apologise for the inconvenience. I will update our records.":
   "അസൗകര്യത്തിന് ക്ഷമിക്കണം. ഞാൻ ഞങ്ങളുടെ രേഖകൾ അപ്ഡേറ്റ് ചെയ്യാം.",
 "I understand. May we call you back later today?":
   "മനസ്സിലായി. ഇന്ന് പിന്നീട് വിളിക്കട്ടെ?",
 "That is perfectly alright. Thank you for your time, and have a good day.":
   "കുഴപ്പമില്ല. നിങ്ങളുടെ സമയത്തിന് നന്ദി, നല്ല ദിവസം ആശംസിക്കുന്നു.",
 "Thank you. Have a good day.": "നന്ദി. നല്ല ദിവസം ആശംസിക്കുന്നു.",
 "I have noted your request. You will not receive further promotional calls from us. Thank you.":
   "നിങ്ങളുടെ അഭ്യർത്ഥന രേഖപ്പെടുത്തി. ഇനി ഞങ്ങളിൽ നിന്ന് പ്രൊമോഷണൽ കോളുകൾ വരില്ല. നന്ദി.",
 "Thank you, and sorry for the disturbance.": "നന്ദി, ശല്യത്തിന് ക്ഷമിക്കണം.",
 "I am ending the call now. Thank you.": "ഞാൻ ഇപ്പോൾ കോൾ അവസാനിപ്പിക്കുന്നു. നന്ദി.",
 "I am unable to hear you. We will try again another time. Thank you.":
   "നിങ്ങളുടെ ശബ്ദം കേൾക്കാൻ കഴിയുന്നില്ല. മറ്റൊരു സമയത്ത് ശ്രമിക്കാം. നന്ദി.",
 "I am sorry, I could not hear you. Are you still there?":
   "ക്ഷമിക്കണം, കേൾക്കാൻ കഴിഞ്ഞില്ല. നിങ്ങൾ ലൈനിൽ ഉണ്ടോ?",
 "Certainly.": "തീർച്ചയായും.",
 "That is a good question, and I would rather our advisor answer it properly for you.":
   "ഇത് നല്ല ചോദ്യമാണ്, ഇതിന് ഞങ്ങളുടെ അഡ്വൈസർ ശരിയായ ഉത്തരം നൽകുന്നതാകും നല്ലത്.",
 "I am {agent_display_name}, calling on behalf of {brand_name}.":
   "ഞാൻ {agent_display_name}, {brand_name} ന് വേണ്ടി വിളിക്കുന്നു.",
 "This call is recorded for quality and training purposes.":
   "ഈ കോൾ ക്വാളിറ്റി, ട്രെയിനിംഗ് ആവശ്യങ്ങൾക്കായി റെക്കോർഡ് ചെയ്യുന്നു.",
 "This conversion carries interest of {roi_annual_pct} percent per annum and a one-time processing fee of {processing_fee} rupees. Goods and services tax applies as per government rules.":
   "ഈ കൺവേർഷന് വർഷത്തിൽ {roi_annual_pct} ശതമാനം പലിശയും {processing_fee} രൂപയുടെ ഒറ്റത്തവണ പ്രോസസിംഗ് ഫീസും ഉണ്ട്. ജിഎസ്ടി സർക്കാർ നിയമപ്രകാരം ബാധകമാണ്.",
 "The revised limit is subject to the terms and conditions of your card agreement.":
   "പുതുക്കിയ ലിമിറ്റ് നിങ്ങളുടെ കാർഡ് കരാറിന്റെ നിബന്ധനകൾക്ക് വിധേയമാണ്.",
 "This card carries a joining fee of {joining_fee} rupees and an annual fee of {annual_fee} rupees, which is reversed on {fee_waiver_condition}.":
   "ഈ കാർഡിന് {joining_fee} രൂപ ജോയിനിംഗ് ഫീസും {annual_fee} രൂപ വാർഷിക ഫീസും ഉണ്ട്, അത് {fee_waiver_condition} ൽ തിരികെ നൽകും.",
 "I will now connect you to our advisor, who will confirm your details and complete the process.":
   "ഞാൻ ഇപ്പോൾ നിങ്ങളെ ഞങ്ങളുടെ അഡ്വൈസറുമായി ബന്ധിപ്പിക്കുന്നു, അവർ നിങ്ങളുടെ വിശദാംശങ്ങൾ സ്ഥിരീകരിച്ച് നടപടി പൂർത്തിയാക്കും.",
}

if __name__ == "__main__":
    sys.exit(apply(["ta", "te", "kn", "ml"]))
