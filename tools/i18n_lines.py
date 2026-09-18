#!/usr/bin/env python3
"""Spoken lines and disclosures in the seven remaining languages.

    python tools/i18n_lines.py

Keyed by the English source string, so the eighteen lines shared across products are translated
once and applied everywhere.

EVERY TRANSLATION IS CHECKED FOR SLOT PARITY before it is written. A translation that silently
drops {eligible_amount} does not crash - it plays a grammatical sentence that states the offer
wrongly, on a recorded line, at a bank. That is the worst possible failure mode of this file, so
it is the one thing the applier refuses to let through.

Register is deliberately conversational, not textbook. Real agents and real customers keep the
product nouns in English - "credit card", "EMI", "limit", "offer", "advisor" - and inflect them
with local grammar. A pure-register translation would be correct and would sound nothing like a
call centre.

All synthetic. Replaced wholesale when SBIC supplies the BLC-approved script per language.
"""

import io
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SLOT = re.compile(r"\{([a-z_]+)\}")

L = {}

# ---------------------------------------------------------------------- Marathi
L["mr"] = {
 "Hello, good day.": "नमस्कार.",
 "Am I speaking with {customer_first_name}?": "मी {customer_first_name} यांच्याशी बोलतोय का?",
 "I am calling about an offer available on your card. It will take about a minute.":
   "मी तुमच्या कार्डवरील एका ऑफरबद्दल कॉल करतोय. फक्त एक मिनिट लागेल.",
 "I am calling about your card limit. It will take less than a minute.":
   "मी तुमच्या कार्ड लिमिटबद्दल कॉल करतोय. एका मिनिटापेक्षा कमी वेळ लागेल.",
 "I am calling about an additional card available to you. It will take about a minute.":
   "मी तुमच्यासाठी उपलब्ध असलेल्या अतिरिक्त कार्डबद्दल कॉल करतोय. सुमारे एक मिनिट लागेल.",
 "You are eligible to convert purchases above {min_txn_amt} rupees into easy monthly instalments. On your card, up to {eligible_amount} rupees can be converted over {tenure_options}.":
   "तुम्ही {min_txn_amt} रुपयांवरील खरेदी सोप्या मासिक हप्त्यांमध्ये बदलू शकता. तुमच्या कार्डवर {eligible_amount} रुपयांपर्यंत, {tenure_options} मध्ये बदलता येईल.",
 "Based on your card usage, your credit limit can be increased from {current_limit} rupees to {enhanced_limit} rupees.":
   "तुमच्या कार्ड वापरानुसार, तुमची क्रेडिट लिमिट {current_limit} रुपयांवरून {enhanced_limit} रुपयांपर्यंत वाढू शकते.",
 "You are eligible for an additional {brand_name} card, the {offered_card_name}, which offers {headline_benefit}.":
   "तुम्ही अतिरिक्त {brand_name} कार्डसाठी पात्र आहात, {offered_card_name}, ज्यामध्ये {headline_benefit} मिळते.",
 "At a tenure of {tenure_months} months, your indicative instalment would be about {indicative_emi} rupees per month.":
   "{tenure_months} महिन्यांच्या मुदतीवर, तुमचा अंदाजे हप्ता दरमहा सुमारे {indicative_emi} रुपये असेल.",
 "This offer is open for {offer_valid_days} days.": "ही ऑफर {offer_valid_days} दिवस उपलब्ध आहे.",
 "The card is issued subject to approval.": "कार्ड मंजुरीच्या अधीन राहून दिले जाते.",
 "Shall I connect you to our advisor to take this forward?":
   "पुढे जाण्यासाठी मी तुम्हाला आमच्या अ‍ॅडव्हायझरशी जोडू का?",
 "Shall I connect you to our advisor to complete this?":
   "हे पूर्ण करण्यासाठी मी तुम्हाला आमच्या अ‍ॅडव्हायझरशी जोडू का?",
 "Thank you. Please stay on the line.": "धन्यवाद. कृपया लाइनवर थांबा.",
 "Of course. The offer is open for {offer_valid_days} days. Would you prefer that our advisor explains the details now, or should we call you back?":
   "नक्कीच. ही ऑफर {offer_valid_days} दिवस उपलब्ध आहे. आमच्या अ‍ॅडव्हायझरने आत्ता तपशील सांगावा, की आम्ही परत कॉल करू?",
 "Of course. The offer stays open for {offer_valid_days} days. Would you like our advisor to explain it now, or should we call you back?":
   "नक्कीच. ही ऑफर {offer_valid_days} दिवस उपलब्ध राहील. आमच्या अ‍ॅडव्हायझरने आत्ता समजावून सांगावे, की आम्ही परत कॉल करू?",
 "Of course. Would you prefer that our advisor explains the details now, or should we call you back?":
   "नक्कीच. आमच्या अ‍ॅडव्हायझरने आत्ता तपशील सांगावा, की आम्ही परत कॉल करू?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can also verify this offer on your {brand_name} app, or by calling the number printed on the back of your card. Shall I continue?":
   "हा योग्य प्रश्न आहे. मी तुमचा कार्ड नंबर, पिन किंवा ओटीपी मागत नाही, आणि कधीही मागणार नाही. तुम्ही ही ऑफर तुमच्या {brand_name} अ‍ॅपवर, किंवा कार्डच्या मागे छापलेल्या नंबरवर कॉल करून तपासू शकता. मी पुढे बोलू का?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can verify this on your {brand_name} app, or on the number printed on the back of your card. Shall I continue?":
   "हा योग्य प्रश्न आहे. मी तुमचा कार्ड नंबर, पिन किंवा ओटीपी मागत नाही, आणि कधीही मागणार नाही. तुम्ही हे तुमच्या {brand_name} अ‍ॅपवर, किंवा कार्डच्या मागे छापलेल्या नंबरवर तपासू शकता. मी पुढे बोलू का?",
 "I am calling on the number registered with your {brand_name} card account. If you would prefer not to receive such calls, I can note that right away.":
   "मी तुमच्या {brand_name} कार्ड खात्यावर नोंदणीकृत नंबरवर कॉल करतोय. तुम्हाला असे कॉल नको असतील, तर मी लगेच नोंद करू शकतो.",
 "That is understandable. A higher limit does not change what you spend, and there is no charge for the increase itself. Would you still like to hear the details from our advisor?":
   "हे समजू शकते. जास्त लिमिटमुळे तुमचा खर्च वाढत नाही, आणि लिमिट वाढवण्याचा कोणताही चार्ज नाही. तरीही तुम्ही आमच्या अ‍ॅडव्हायझरकडून तपशील ऐकू इच्छिता का?",
 "Many customers do hold more than one card, and each card carries its own benefits. Would you like our advisor to explain how this one differs from your existing card?":
   "बरेच ग्राहक एकापेक्षा जास्त कार्ड ठेवतात, आणि प्रत्येक कार्डचे स्वतःचे फायदे असतात. हे कार्ड तुमच्या सध्याच्या कार्डपेक्षा कसे वेगळे आहे, हे आमच्या अ‍ॅडव्हायझरने सांगावे का?",
 "Certainly. We will call you back at a more convenient time.":
   "नक्कीच. आम्ही तुम्हाला सोयीच्या वेळी परत कॉल करू.",
 "I apologise for the inconvenience. I will update our records.":
   "गैरसोयीबद्दल क्षमस्व. मी आमच्या रेकॉर्डमध्ये अपडेट करतो.",
 "I understand. May we call you back later today?":
   "मी समजू शकतो. आम्ही तुम्हाला आज नंतर कॉल करू का?",
 "That is perfectly alright. Thank you for your time, and have a good day.":
   "काही हरकत नाही. तुमच्या वेळेबद्दल धन्यवाद, तुमचा दिवस चांगला जावो.",
 "Thank you. Have a good day.": "धन्यवाद. तुमचा दिवस चांगला जावो.",
 "I have noted your request. You will not receive further promotional calls from us. Thank you.":
   "मी तुमची विनंती नोंदवली आहे. तुम्हाला यापुढे आमच्याकडून प्रमोशनल कॉल येणार नाहीत. धन्यवाद.",
 "Thank you, and sorry for the disturbance.": "धन्यवाद, आणि त्रासाबद्दल क्षमस्व.",
 "I am ending the call now. Thank you.": "मी आता कॉल बंद करतोय. धन्यवाद.",
 "I am unable to hear you. We will try again another time. Thank you.":
   "मला तुमचा आवाज ऐकू येत नाही. आम्ही पुन्हा कधीतरी प्रयत्न करू. धन्यवाद.",
 "I am sorry, I could not hear you. Are you still there?":
   "माफ करा, मला ऐकू आले नाही. तुम्ही लाइनवर आहात का?",
 "Certainly.": "नक्कीच.",
 "That is a good question, and I would rather our advisor answer it properly for you.":
   "हा चांगला प्रश्न आहे, आणि याचे योग्य उत्तर आमच्या अ‍ॅडव्हायझरनेच द्यावे असे मला वाटते.",
 # disclosures
 "I am {agent_display_name}, calling on behalf of {brand_name}.":
   "मी {agent_display_name}, {brand_name} च्या वतीने कॉल करतोय.",
 "This call is recorded for quality and training purposes.":
   "हा कॉल क्वालिटी आणि ट्रेनिंगसाठी रेकॉर्ड केला जातोय.",
 "This conversion carries interest of {roi_annual_pct} percent per annum and a one-time processing fee of {processing_fee} rupees. Goods and services tax applies as per government rules.":
   "या कन्व्हर्जनवर वार्षिक {roi_annual_pct} टक्के व्याज आणि {processing_fee} रुपयांचा एकवेळचा प्रोसेसिंग फी लागतो. जीएसटी सरकारी नियमांनुसार लागू होईल.",
 "The revised limit is subject to the terms and conditions of your card agreement.":
   "सुधारित लिमिट तुमच्या कार्ड कराराच्या अटी आणि शर्तींच्या अधीन आहे.",
 "This card carries a joining fee of {joining_fee} rupees and an annual fee of {annual_fee} rupees, which is reversed on {fee_waiver_condition}.":
   "या कार्डवर {joining_fee} रुपये जॉइनिंग फी आणि {annual_fee} रुपये वार्षिक फी आहे, जी {fee_waiver_condition} वर परत केली जाते.",
 "I will now connect you to our advisor, who will confirm your details and complete the process.":
   "मी आता तुम्हाला आमच्या अ‍ॅडव्हायझरशी जोडतोय, जे तुमचे तपशील कन्फर्म करून प्रक्रिया पूर्ण करतील.",
}

# ---------------------------------------------------------------------- Gujarati
L["gu"] = {
 "Hello, good day.": "નમસ્તે.",
 "Am I speaking with {customer_first_name}?": "શું હું {customer_first_name} સાથે વાત કરું છું?",
 "I am calling about an offer available on your card. It will take about a minute.":
   "હું તમારા કાર્ડ પરની એક ઓફર વિશે કોલ કરું છું. લગભગ એક મિનિટ લાગશે.",
 "I am calling about your card limit. It will take less than a minute.":
   "હું તમારી કાર્ડ લિમિટ વિશે કોલ કરું છું. એક મિનિટથી ઓછો સમય લાગશે.",
 "I am calling about an additional card available to you. It will take about a minute.":
   "હું તમારા માટે ઉપલબ્ધ વધારાના કાર્ડ વિશે કોલ કરું છું. લગભગ એક મિનિટ લાગશે.",
 "You are eligible to convert purchases above {min_txn_amt} rupees into easy monthly instalments. On your card, up to {eligible_amount} rupees can be converted over {tenure_options}.":
   "તમે {min_txn_amt} રૂપિયાથી વધુની ખરીદીને સરળ માસિક હપ્તામાં ફેરવી શકો છો. તમારા કાર્ડ પર {eligible_amount} રૂપિયા સુધી, {tenure_options} માં ફેરવી શકાય છે.",
 "Based on your card usage, your credit limit can be increased from {current_limit} rupees to {enhanced_limit} rupees.":
   "તમારા કાર્ડ વપરાશના આધારે, તમારી ક્રેડિટ લિમિટ {current_limit} રૂપિયાથી વધીને {enhanced_limit} રૂપિયા થઈ શકે છે.",
 "You are eligible for an additional {brand_name} card, the {offered_card_name}, which offers {headline_benefit}.":
   "તમે વધારાના {brand_name} કાર્ડ માટે પાત્ર છો, {offered_card_name}, જેમાં {headline_benefit} મળે છે.",
 "At a tenure of {tenure_months} months, your indicative instalment would be about {indicative_emi} rupees per month.":
   "{tenure_months} મહિનાની મુદત પર, તમારો અંદાજિત હપ્તો દર મહિને લગભગ {indicative_emi} રૂપિયા થશે.",
 "This offer is open for {offer_valid_days} days.": "આ ઓફર {offer_valid_days} દિવસ સુધી ખુલ્લી છે.",
 "The card is issued subject to approval.": "કાર્ડ મંજૂરીને આધીન આપવામાં આવે છે.",
 "Shall I connect you to our advisor to take this forward?":
   "આગળ વધવા માટે હું તમને અમારા એડવાઇઝર સાથે જોડું?",
 "Shall I connect you to our advisor to complete this?":
   "આ પૂર્ણ કરવા માટે હું તમને અમારા એડવાઇઝર સાથે જોડું?",
 "Thank you. Please stay on the line.": "આભાર. કૃપા કરીને લાઇન પર રહો.",
 "Of course. The offer is open for {offer_valid_days} days. Would you prefer that our advisor explains the details now, or should we call you back?":
   "ચોક્કસ. આ ઓફર {offer_valid_days} દિવસ ખુલ્લી છે. અમારા એડવાઇઝર અત્યારે વિગતો સમજાવે, કે અમે પાછા કોલ કરીએ?",
 "Of course. The offer stays open for {offer_valid_days} days. Would you like our advisor to explain it now, or should we call you back?":
   "ચોક્કસ. આ ઓફર {offer_valid_days} દિવસ ખુલ્લી રહેશે. અમારા એડવાઇઝર અત્યારે સમજાવે, કે અમે પાછા કોલ કરીએ?",
 "Of course. Would you prefer that our advisor explains the details now, or should we call you back?":
   "ચોક્કસ. અમારા એડવાઇઝર અત્યારે વિગતો સમજાવે, કે અમે પાછા કોલ કરીએ?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can also verify this offer on your {brand_name} app, or by calling the number printed on the back of your card. Shall I continue?":
   "આ યોગ્ય પ્રશ્ન છે. હું તમારો કાર્ડ નંબર, પિન કે ઓટીપી માંગતો નથી, અને ક્યારેય માંગીશ નહીં. તમે આ ઓફર તમારી {brand_name} એપ પર, અથવા કાર્ડની પાછળ છપાયેલા નંબર પર કોલ કરીને ચકાસી શકો છો. હું આગળ વધું?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can verify this on your {brand_name} app, or on the number printed on the back of your card. Shall I continue?":
   "આ યોગ્ય પ્રશ્ન છે. હું તમારો કાર્ડ નંબર, પિન કે ઓટીપી માંગતો નથી, અને ક્યારેય માંગીશ નહીં. તમે આ તમારી {brand_name} એપ પર, અથવા કાર્ડની પાછળ છપાયેલા નંબર પર ચકાસી શકો છો. હું આગળ વધું?",
 "I am calling on the number registered with your {brand_name} card account. If you would prefer not to receive such calls, I can note that right away.":
   "હું તમારા {brand_name} કાર્ડ એકાઉન્ટ પર રજિસ્ટર્ડ નંબર પર કોલ કરું છું. તમને આવા કોલ ન જોઈતા હોય, તો હું તરત નોંધી શકું છું.",
 "That is understandable. A higher limit does not change what you spend, and there is no charge for the increase itself. Would you still like to hear the details from our advisor?":
   "આ સમજી શકાય એવું છે. વધારે લિમિટથી તમારો ખર્ચ વધતો નથી, અને લિમિટ વધારવાનો કોઈ ચાર્જ નથી. તો પણ તમે અમારા એડવાઇઝર પાસેથી વિગતો સાંભળવા માંગશો?",
 "Many customers do hold more than one card, and each card carries its own benefits. Would you like our advisor to explain how this one differs from your existing card?":
   "ઘણા ગ્રાહકો એકથી વધુ કાર્ડ રાખે છે, અને દરેક કાર્ડના પોતાના ફાયદા હોય છે. આ કાર્ડ તમારા હાલના કાર્ડથી કેવી રીતે અલગ છે એ અમારા એડવાઇઝર સમજાવે?",
 "Certainly. We will call you back at a more convenient time.":
   "ચોક્કસ. અમે તમને અનુકૂળ સમયે પાછા કોલ કરીશું.",
 "I apologise for the inconvenience. I will update our records.":
   "અસુવિધા બદલ માફ કરશો. હું અમારા રેકોર્ડમાં અપડેટ કરીશ.",
 "I understand. May we call you back later today?":
   "હું સમજી શકું છું. અમે તમને આજે પછી કોલ કરીએ?",
 "That is perfectly alright. Thank you for your time, and have a good day.":
   "કોઈ વાંધો નથી. તમારા સમય બદલ આભાર, તમારો દિવસ સારો રહે.",
 "Thank you. Have a good day.": "આભાર. તમારો દિવસ સારો રહે.",
 "I have noted your request. You will not receive further promotional calls from us. Thank you.":
   "મેં તમારી વિનંતી નોંધી લીધી છે. તમને હવે પછી અમારા તરફથી પ્રમોશનલ કોલ નહીં આવે. આભાર.",
 "Thank you, and sorry for the disturbance.": "આભાર, અને ખલેલ બદલ માફ કરશો.",
 "I am ending the call now. Thank you.": "હું હવે કોલ બંધ કરું છું. આભાર.",
 "I am unable to hear you. We will try again another time. Thank you.":
   "મને તમારો અવાજ સંભળાતો નથી. અમે ફરી કોઈ વાર પ્રયત્ન કરીશું. આભાર.",
 "I am sorry, I could not hear you. Are you still there?":
   "માફ કરશો, મને સંભળાયું નહીં. તમે લાઇન પર છો?",
 "Certainly.": "ચોક્કસ.",
 "That is a good question, and I would rather our advisor answer it properly for you.":
   "આ સારો પ્રશ્ન છે, અને એનો યોગ્ય જવાબ અમારા એડવાઇઝર આપે એ વધુ સારું રહેશે.",
 "I am {agent_display_name}, calling on behalf of {brand_name}.":
   "હું {agent_display_name}, {brand_name} વતી કોલ કરું છું.",
 "This call is recorded for quality and training purposes.":
   "આ કોલ ક્વોલિટી અને ટ્રેનિંગ માટે રેકોર્ડ થાય છે.",
 "This conversion carries interest of {roi_annual_pct} percent per annum and a one-time processing fee of {processing_fee} rupees. Goods and services tax applies as per government rules.":
   "આ કન્વર્ઝન પર વાર્ષિક {roi_annual_pct} ટકા વ્યાજ અને {processing_fee} રૂપિયાની એક વખતની પ્રોસેસિંગ ફી લાગે છે. જીએસટી સરકારી નિયમો મુજબ લાગુ થશે.",
 "The revised limit is subject to the terms and conditions of your card agreement.":
   "સુધારેલી લિમિટ તમારા કાર્ડ કરારની શરતોને આધીન છે.",
 "This card carries a joining fee of {joining_fee} rupees and an annual fee of {annual_fee} rupees, which is reversed on {fee_waiver_condition}.":
   "આ કાર્ડ પર {joining_fee} રૂપિયા જોઇનિંગ ફી અને {annual_fee} રૂપિયા વાર્ષિક ફી છે, જે {fee_waiver_condition} પર પાછી મળે છે.",
 "I will now connect you to our advisor, who will confirm your details and complete the process.":
   "હું હવે તમને અમારા એડવાઇઝર સાથે જોડું છું, જે તમારી વિગતો કન્ફર્મ કરીને પ્રક્રિયા પૂર્ણ કરશે.",
}

# ---------------------------------------------------------------------- Bengali
L["bn"] = {
 "Hello, good day.": "নমস্কার.",
 "Am I speaking with {customer_first_name}?": "আমি কি {customer_first_name} এর সাথে কথা বলছি?",
 "I am calling about an offer available on your card. It will take about a minute.":
   "আমি আপনার কার্ডে থাকা একটি অফার নিয়ে কল করছি। প্রায় এক মিনিট লাগবে।",
 "I am calling about your card limit. It will take less than a minute.":
   "আমি আপনার কার্ড লিমিট নিয়ে কল করছি। এক মিনিটেরও কম সময় লাগবে।",
 "I am calling about an additional card available to you. It will take about a minute.":
   "আমি আপনার জন্য উপলব্ধ একটি অতিরিক্ত কার্ড নিয়ে কল করছি। প্রায় এক মিনিট লাগবে।",
 "You are eligible to convert purchases above {min_txn_amt} rupees into easy monthly instalments. On your card, up to {eligible_amount} rupees can be converted over {tenure_options}.":
   "আপনি {min_txn_amt} টাকার উপরের কেনাকাটা সহজ মাসিক কিস্তিতে পরিবর্তন করতে পারেন। আপনার কার্ডে {eligible_amount} টাকা পর্যন্ত, {tenure_options} এ পরিবর্তন করা যাবে।",
 "Based on your card usage, your credit limit can be increased from {current_limit} rupees to {enhanced_limit} rupees.":
   "আপনার কার্ড ব্যবহারের ভিত্তিতে, আপনার ক্রেডিট লিমিট {current_limit} টাকা থেকে বেড়ে {enhanced_limit} টাকা হতে পারে।",
 "You are eligible for an additional {brand_name} card, the {offered_card_name}, which offers {headline_benefit}.":
   "আপনি একটি অতিরিক্ত {brand_name} কার্ডের জন্য যোগ্য, {offered_card_name}, যাতে {headline_benefit} পাওয়া যায়।",
 "At a tenure of {tenure_months} months, your indicative instalment would be about {indicative_emi} rupees per month.":
   "{tenure_months} মাসের মেয়াদে, আপনার আনুমানিক কিস্তি মাসে প্রায় {indicative_emi} টাকা হবে।",
 "This offer is open for {offer_valid_days} days.": "এই অফারটি {offer_valid_days} দিন খোলা আছে।",
 "The card is issued subject to approval.": "কার্ড অনুমোদন সাপেক্ষে দেওয়া হয়।",
 "Shall I connect you to our advisor to take this forward?":
   "এগিয়ে যাওয়ার জন্য আমি কি আপনাকে আমাদের অ্যাডভাইজারের সাথে যুক্ত করব?",
 "Shall I connect you to our advisor to complete this?":
   "এটি সম্পূর্ণ করার জন্য আমি কি আপনাকে আমাদের অ্যাডভাইজারের সাথে যুক্ত করব?",
 "Thank you. Please stay on the line.": "ধন্যবাদ। অনুগ্রহ করে লাইনে থাকুন।",
 "Of course. The offer is open for {offer_valid_days} days. Would you prefer that our advisor explains the details now, or should we call you back?":
   "অবশ্যই। অফারটি {offer_valid_days} দিন খোলা আছে। আমাদের অ্যাডভাইজার এখন বিস্তারিত বলবেন, নাকি আমরা পরে কল করব?",
 "Of course. The offer stays open for {offer_valid_days} days. Would you like our advisor to explain it now, or should we call you back?":
   "অবশ্যই। অফারটি {offer_valid_days} দিন খোলা থাকবে। আমাদের অ্যাডভাইজার এখন বুঝিয়ে বলবেন, নাকি আমরা পরে কল করব?",
 "Of course. Would you prefer that our advisor explains the details now, or should we call you back?":
   "অবশ্যই। আমাদের অ্যাডভাইজার এখন বিস্তারিত বলবেন, নাকি আমরা পরে কল করব?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can also verify this offer on your {brand_name} app, or by calling the number printed on the back of your card. Shall I continue?":
   "এটি একটি যুক্তিসঙ্গত প্রশ্ন। আমি আপনার কার্ড নম্বর, পিন বা ওটিপি চাইছি না, এবং কখনও চাইব না। আপনি এই অফারটি আপনার {brand_name} অ্যাপে, অথবা কার্ডের পিছনে ছাপা নম্বরে কল করে যাচাই করতে পারেন। আমি কি এগিয়ে যাব?",
 "That is a fair question. I am not asking for any card number, PIN or OTP, and I never will. You can verify this on your {brand_name} app, or on the number printed on the back of your card. Shall I continue?":
   "এটি একটি যুক্তিসঙ্গত প্রশ্ন। আমি আপনার কার্ড নম্বর, পিন বা ওটিপি চাইছি না, এবং কখনও চাইব না। আপনি এটি আপনার {brand_name} অ্যাপে, অথবা কার্ডের পিছনে ছাপা নম্বরে যাচাই করতে পারেন। আমি কি এগিয়ে যাব?",
 "I am calling on the number registered with your {brand_name} card account. If you would prefer not to receive such calls, I can note that right away.":
   "আমি আপনার {brand_name} কার্ড অ্যাকাউন্টে নিবন্ধিত নম্বরে কল করছি। আপনি এ ধরনের কল না চাইলে, আমি এখনই তা নথিভুক্ত করতে পারি।",
 "That is understandable. A higher limit does not change what you spend, and there is no charge for the increase itself. Would you still like to hear the details from our advisor?":
   "এটা বোঝা যায়। বেশি লিমিট আপনার খরচ বাড়ায় না, এবং লিমিট বাড়ানোর কোনো চার্জ নেই। তবুও কি আপনি আমাদের অ্যাডভাইজারের কাছ থেকে বিস্তারিত শুনতে চান?",
 "Many customers do hold more than one card, and each card carries its own benefits. Would you like our advisor to explain how this one differs from your existing card?":
   "অনেক গ্রাহক একাধিক কার্ড রাখেন, এবং প্রতিটি কার্ডের নিজস্ব সুবিধা আছে। এই কার্ডটি আপনার বর্তমান কার্ড থেকে কীভাবে আলাদা, তা কি আমাদের অ্যাডভাইজার বুঝিয়ে বলবেন?",
 "Certainly. We will call you back at a more convenient time.":
   "অবশ্যই। আমরা আপনাকে সুবিধাজনক সময়ে আবার কল করব।",
 "I apologise for the inconvenience. I will update our records.":
   "অসুবিধার জন্য দুঃখিত। আমি আমাদের রেকর্ড আপডেট করে দেব।",
 "I understand. May we call you back later today?":
   "আমি বুঝতে পারছি। আমরা কি আজ পরে আপনাকে কল করব?",
 "That is perfectly alright. Thank you for your time, and have a good day.":
   "কোনো সমস্যা নেই। আপনার সময়ের জন্য ধন্যবাদ, আপনার দিনটি ভালো কাটুক।",
 "Thank you. Have a good day.": "ধন্যবাদ। আপনার দিনটি ভালো কাটুক।",
 "I have noted your request. You will not receive further promotional calls from us. Thank you.":
   "আমি আপনার অনুরোধ নথিভুক্ত করেছি। আপনি আর আমাদের কাছ থেকে প্রমোশনাল কল পাবেন না। ধন্যবাদ।",
 "Thank you, and sorry for the disturbance.": "ধন্যবাদ, এবং বিরক্ত করার জন্য দুঃখিত।",
 "I am ending the call now. Thank you.": "আমি এখন কলটি শেষ করছি। ধন্যবাদ।",
 "I am unable to hear you. We will try again another time. Thank you.":
   "আমি আপনার কথা শুনতে পাচ্ছি না। আমরা অন্য সময় আবার চেষ্টা করব। ধন্যবাদ।",
 "I am sorry, I could not hear you. Are you still there?":
   "দুঃখিত, আমি শুনতে পাইনি। আপনি কি লাইনে আছেন?",
 "Certainly.": "অবশ্যই।",
 "That is a good question, and I would rather our advisor answer it properly for you.":
   "এটি একটি ভালো প্রশ্ন, এবং এর সঠিক উত্তর আমাদের অ্যাডভাইজার দিলেই ভালো হবে।",
 "I am {agent_display_name}, calling on behalf of {brand_name}.":
   "আমি {agent_display_name}, {brand_name} এর পক্ষ থেকে কল করছি।",
 "This call is recorded for quality and training purposes.":
   "এই কলটি গুণমান ও প্রশিক্ষণের জন্য রেকর্ড করা হচ্ছে।",
 "This conversion carries interest of {roi_annual_pct} percent per annum and a one-time processing fee of {processing_fee} rupees. Goods and services tax applies as per government rules.":
   "এই কনভার্সনে বার্ষিক {roi_annual_pct} শতাংশ সুদ এবং {processing_fee} টাকার এককালীন প্রসেসিং ফি প্রযোজ্য। জিএসটি সরকারি নিয়ম অনুযায়ী প্রযোজ্য হবে।",
 "The revised limit is subject to the terms and conditions of your card agreement.":
   "সংশোধিত লিমিট আপনার কার্ড চুক্তির শর্তাবলীর অধীন।",
 "This card carries a joining fee of {joining_fee} rupees and an annual fee of {annual_fee} rupees, which is reversed on {fee_waiver_condition}.":
   "এই কার্ডে {joining_fee} টাকা জয়েনিং ফি এবং {annual_fee} টাকা বার্ষিক ফি আছে, যা {fee_waiver_condition} এ ফেরত দেওয়া হয়।",
 "I will now connect you to our advisor, who will confirm your details and complete the process.":
   "আমি এখন আপনাকে আমাদের অ্যাডভাইজারের সাথে যুক্ত করছি, যিনি আপনার তথ্য নিশ্চিত করে প্রক্রিয়াটি সম্পূর্ণ করবেন।",
}


def apply(locales=None):
    content_dir = ROOT / "content"
    targets = locales or sorted(L)
    stats = {"lines": 0, "disclosures": 0, "skipped": 0}
    problems = []

    def translate(english, locale):
        """Look up, and refuse anything that loses a campaign variable."""
        out = L[locale].get(english)
        if not out:
            stats["skipped"] += 1
            return None
        if set(SLOT.findall(english)) != set(SLOT.findall(out)):
            problems.append(f"{locale}: slot mismatch\n    en: {english[:70]}\n    {locale}: {out[:70]}")
            return None
        return out

    for path in sorted((content_dir / "script").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        for node in doc["nodes"]:
            english = (node.get("line") or {}).get("en", "").strip()
            if not english:
                continue
            for locale in targets:
                got = translate(english, locale)
                if got:
                    node["line"][locale] = got
                    stats["lines"] += 1
        head = path.read_text(encoding="utf-8").split("product:")[0]
        path.write_text(head + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True,
                                              width=200), encoding="utf-8")

    dpath = content_dir / "disclosures.yaml"
    ddoc = yaml.safe_load(dpath.read_text(encoding="utf-8"))
    for spec in ddoc["disclosures"].values():
        english = " ".join(spec["line"]["en"].split())
        for locale in targets:
            got = translate(english, locale)
            if got:
                spec["line"][locale] = got
                stats["disclosures"] += 1
    head = dpath.read_text(encoding="utf-8").split("version:")[0]
    dpath.write_text(head + yaml.safe_dump(ddoc, sort_keys=False, allow_unicode=True, width=200),
                     encoding="utf-8")

    for p in problems:
        print("  SLOT MISMATCH " + p)
    print(f"  {stats['lines']} node lines, {stats['disclosures']} disclosures translated")
    print(f"  {stats['skipped']} lookups had no translation (expected while batches land)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(apply())
