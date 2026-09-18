# SBI Card Outbound Voice AI: Complete Engagement Brief

**TransOrg Analytics · Internal reference document · September 2026**

*Everything on this engagement in one place: the problem, the domain, the economics, the competition, our approach, the architecture, the roadmap, and what is still owed.*

---

## Contents

1. [Executive summary](#1-executive-summary)
2. [How this started](#2-how-this-started)
3. [Domain primer: the vocabulary of this business](#3-domain-primer-the-vocabulary-of-this-business)
4. [The business problem](#4-the-business-problem)
5. [What is actually being sold](#5-what-is-actually-being-sold)
6. [The economics](#6-the-economics)
7. [The competitive field](#7-the-competitive-field)
8. [Our approach and positioning](#8-our-approach-and-positioning)
9. [Technical architecture](#9-technical-architecture)
10. [Build roadmap](#10-build-roadmap)
11. [What we have produced so far](#11-what-we-have-produced-so-far)
12. [Deliverables to SBI Card](#12-deliverables-to-sbi-card)
13. [Open questions, risks and corrections](#13-open-questions-risks-and-corrections)
14. [Appendix: assumptions register and glossary](#14-appendix-assumptions-register-and-glossary)

---

## 1. Executive summary

SBI Card runs a 2,000-plus seat outbound telecalling operation that sells three things to existing cardholders: FlexiPay, which is a loan on the card, Multicarding, which is a second card, and CLIP, which is a credit limit increase. Every call is handled end to end by a human advisor after the vendor dialer connects it.

They want an AI voice bot to take over the front of that call. The bot greets, verifies softly, pitches from an approved script, answers questions from an approved FAQ list, and detects whether the customer is interested. If they are, it hands the call warm to a human advisor who verifies identity, captures consent and books the sale. Nothing about the approval step is automated, because it is compliance sensitive.

The engagement is at POC stage. No RFP yet, and the formal RFP is expected in FY2027 to 28. SBI Card is running a three-month evaluation with three AI bot partners in parallel. A competing vendor, unfyd.AI, has already quoted Rs 9 per contacted minute, which is roughly Rs 2.76 crore a month at Phase-1 volume.

**Four things define this deal.**

First, it is a wedge, not a replacement. The bot owns roughly the first ninety seconds of the call and nothing else. The data pipeline, the dialer, the consent capture and the booking all stay exactly as they are.

Second, we are a sub-vendor. The commercial structure in SBI Card's own charter puts the master service agreement between the calling partner and the AI bot partner, with payment flowing as a monthly cost reimbursement to the calling partner. SBI Card picks the winner, the agency signs the paper.

Third, cost reduction is a stated design constraint, not a hoped-for outcome. Automation that raises total cost per booking is explicitly non-viable.

Fourth, we are not the strongest voice vendor in the room and we know it. Shrey's own brief says competing vendors have stronger voice-specific outbound experience and that our differentiation must come from domain and analytics depth plus execution speed.

**Our position, in one sentence.** We are the only bidder proposing to model propensity to convert on SBI Card's own cross-sell history, and to prove the saving against a human control arm running the same base.

---

## 2. How this started

### The first email, 27 August 2026

Shrey Bhardwaj, Industry Engagement Head, wrote to Sushane, Shuchita, Vishad and Naveen after an in-person meeting with SBI Card. The client-side contacts are Saikat and Sumit Talreja, with Sumit as the anchor point of contact.

The email set out the opportunity, the client's current setup, what they want solved, the competitive context, and three asks of the team.

**The three asks, in Shrey's stated order:**

1. Draft a proposed use case, one-pager or approach note, or a demo, covering the voice bot layer, multilingual handling and human handoff logic. This goes to the client first.
2. Once SBI Card shares their requirements document, make an SME available for a clarification call.
3. Following that, prepare a proposed architecture covering dialer integration approach, bot and NLU stack, language support strategy, handoff and escalation logic, and cost-efficiency levers.

Note what is deliberately held back from the first ask. No architecture, no dialer integration, no cost levers. Those all belong to the third deliverable.

### The second email, 2 September 2026

Shrey forwarded an additional requirements document from SBI Cards. This is the AI-BOT charter deck, and it is the single most useful artefact in the whole engagement. It contains:

- The proposed AI BOT and advisor call workflow process map, in seven numbered steps
- Three key commercial pointers about how the contract is structured
- A seven-component feature list titled "Project Scope: AI Voice Platform Features"
- The unfyd.AI benchmark of Rs 9 per contacted minute and Rs 2.76 crore a month
- Current-state and proposed-state process flowcharts for FlexiPay, Multicarding and CLIP
- A Phase 1 scope slide naming the three products and their targets

### The cast, and why it matters more than the technology

There are five actors in this deal, and TransOrg is not the one you would assume.

**SBI Card.** Owns the customer, the calling base, the offers, the approved script and the FAQ glossary. Their internal teams include Analytics and IT who build the base, IMAC who encrypt and transfer it, MIS Operations who prepare campaign files, and Agency Operations who liaise with the vendor.

**The calling partner.** The telecom and dialer vendor running the 2,000-plus seat operation. They own the dialer, the SIP trunk, the advisors and the CRM. Critically, they are the counterparty we would contract with.

**The AI bot partner.** The slot TransOrg is competing for, alongside two other vendors during the three-month POC.

**The advisor.** Employed by the calling partner, not by SBI Card. Handles verification, consent and booking.

**The customer.** An existing SBI Card cardholder, pre-approved for the offer, being called cold.

**The commercial structure, verbatim from the charter's three key pointers:**

- Master Service Agreement between the calling partner and the AI bot partner
- Encrypted API integration between the calling partner's CRM API and the AI bot dialer API
- Monthly cost reimbursement to the calling partner as per original utilisation submitted by the AI bot partner, as part of IT integration cost in the existing statement of work

This means we would be a sub-vendor to SBI Card's telecalling agency, paid through that agency's contract. It changes who we sell to, who owns the paper, and what our margin structure looks like. It is easy to miss and it is the most important structural fact in the deal.

### Timeline and gates

- POC stage now, no formal RFP
- Three-month POC, three AI bot partners evaluated in parallel
- RFP expected FY2027 to 28
- If selected: NDA first, then InfoSec review, then any implementation work

---

## 3. Domain primer: the vocabulary of this business

This section exists so anyone picking up the engagement can follow a client conversation without stopping. Skip it if you already know the terrain.

### 3.1 Outbound versus inbound

The simplest split in all of call centres is who dialled whom.

**Inbound** means the customer calls you. They have a problem or an intent, they arrive already engaged, and your job is to solve it and perhaps sell something on the way out. Think of a shop with a customer walking through the door.

**Outbound** means you call the customer. They were not thinking about you. You are interrupting dinner, and your job is to earn thirty seconds of attention before they hang up. Think of knocking on doors down a street.

| | Inbound | Outbound |
|---|---|---|
| Who initiates | Customer | Company |
| Customer mood | Engaged, sometimes annoyed | Indifferent, often annoyed |
| Typical success rate | High | Low, 1 to 3 percent |
| Main cost driver | Handle time | Wasted dial attempts |
| Regulation | Light | Heavy: do-not-call lists, calling hours |
| Metric that matters | Resolution, satisfaction | Conversion, cost per sale |

**This engagement is entirely outbound.** That is why the numbers are brutal, why regulation is tight, and why cost per booking rather than cost per call is the number that decides everything.

A third category worth knowing is **blended**, where agents take inbound when queues are busy and dial outbound when they are not. SBI Card's operation is dedicated outbound.

### 3.2 Cross-sell versus upsell

Both mean selling more to an existing customer. The difference is what kind of more.

**Cross-sell** is a different product. Sideways. You have a credit card, here is a personal loan. In fast food terms, would you like fries with that.

**Upsell** is a bigger version of the same product. Upwards. You have a silver card, take the platinum one. Would you like to go large.

Mapped to the three Phase 1 products:

| Product | What it is | Which is it |
|---|---|---|
| FlexiPay | Convert a purchase or outstanding balance into monthly EMIs, effectively a loan on the card | Cross-sell, because it is a lending product not a card |
| Multicarding | Issue a second, different card to an existing cardholder | Cross-sell, a new product in the same family |
| CLIP, or Credit Limit Increase Program | Raise the spending limit on the card they already have | Upsell, more of the same thing |

Two related terms you will hear in the same breath. **Deep-sell** is the same product with more usage, getting them to swipe more rather than selling anything new. **Win-back** is reactivating a dormant customer.

**Why banks obsess over this.** Acquiring a new credit card customer in India costs somewhere between Rs 1,500 and Rs 4,000 once you count marketing, KYC, underwriting and card issuance. Selling FlexiPay to someone who already holds your card costs one phone call. The customer is already verified, already scored, and already has a payment history you can read. That is why a 2,000-seat operation exists purely to call existing cardholders. It is the cheapest growth a bank can buy.

### 3.3 The funnel

Everything in outbound telesales is a funnel that leaks at every stage. On a base of 100,000 records, a realistic month looks like this.

| Stage | Records | What happened |
|---|---|---|
| Records in the calling base | 100,000 | Pre-approved, zone-segmented |
| Dialable after do-not-call scrubbing | 90,000 | About 10 percent removed, legally untouchable |
| Calls connected | 27,000 | Roughly 30 percent connect rate |
| Right party on the line | 21,600 | About 80 percent of connects reach the actual cardholder |
| Said yes to the offer | 2,600 | About 12 percent of real conversations |
| Booked | 1,800 | About 70 percent of yeses survive verification and consent |

**Roughly 1.8 percent of the base turns into a sale.** That is normal for card cross-sell.

Two things to internalise from this.

**Improving an early stage multiplies through everything after it.** Lifting connect rate from 30 to 35 percent adds around 300 sales without changing the pitch at all. This is why a best-time-to-call model is a serious lever and not a nice-to-have.

**Almost all the cost sits in the 21,600 conversations, and almost all the revenue comes from 1,800 of them.** The 19,000 rejections are where the money burns. That is the entire reason a bot is interesting: not because it sells better, but because it can fail cheaper.

### 3.4 The calling machinery

**The dialer** is the software deciding who to call, when, and which agent gets the call. Four modes, and the difference is money.

- **Preview.** The agent sees the file, then clicks to dial. Highest quality, lowest volume, used for high-value accounts.
- **Progressive.** The system dials one number as soon as an agent is free. One call per agent, no wasted calls, moderate volume.
- **Predictive.** The system dials several numbers per free agent, guessing how many will not connect, and routes whoever picks up to whoever is free. Much higher volume, but sometimes a customer answers and nobody is available. That is an abandoned call, and regulators cap the rate.
- **Power.** A fixed multiplier, such as three numbers per agent. A blunter predictive.

SBI Card's flowcharts specify calling initiated in predictive or progressive mode depending on data volume. Large base means predictive, small base means progressive.

**Supporting cast:**

- **ACD, or Automatic Call Distributor.** Routes a live call to the right agent. The "advisor idle pool" in SBI Card's flow is the ACD's queue of free advisors.
- **IVR.** The press-one-to-accept menu. Here it is not a phone tree, it is a consent-capture instrument. The recording of the customer pressing one is the legal evidence they agreed.
- **AMD, or Answering Machine Detection.** Decides whether a human or voicemail picked up. Frequently wrong, which is why bots sometimes pitch to answering machines.
- **CRM.** Where the customer record and the call outcome live. In this deal it is the calling partner's CRM, not SBI Card's.
- **Disposition code.** The tag the agent picks at the end of every call: interested, not interested, callback, wrong number, do-not-call request, language barrier. Dispositions are the raw material for every report and every model we would build.
- **Warm transfer versus cold transfer.** Warm means the first person stays on and introduces the customer. Cold is a blind handoff. SBI Card wants warm, with a screen-pop so the advisor sees context automatically. Without the screen-pop the advisor re-asks everything and the handoff costs more than it saves.
- **Whisper summary.** A short spoken briefing played to the advisor before the customer is connected.

### 3.5 The metrics that decide whether you are winning

**Time metrics**

- **Talk time.** Actual conversation. This is what a contacted minute bills.
- **Wrap, or After Call Work.** The twenty to forty seconds after hanging up spent tagging the disposition. Paid, not billable.
- **AHT, or Average Handle Time.** Talk plus wrap. The headline efficiency number.

**People metrics**

- **Occupancy.** Percentage of logged-in time spent on calls. Seventy to eighty-five percent is healthy, above ninety and people burn out.
- **Utilisation, or talk-time ratio.** Percentage of the shift actually spent talking. Usually thirty to forty-five percent. This is the number that makes the bot economics tight, because an agent costs a full salary but only talks a third of the day.
- **Shrinkage.** The gap between people employed and people on the phone: breaks, training, leave, absenteeism. Typically twenty-five to thirty-five percent.
- **Attrition.** People quitting. Indian outbound telecalling runs sixty to eighty percent a year.

**Money metrics**

- **Cost per contacted minute.** What the vendor bills.
- **Cost per booking, sometimes CPA.** Total cost divided by sales made. This is the only number that actually matters. Everything else is an input to it.
- **Seat cost.** Fully loaded monthly cost of one agent, including salary, incentive, share of supervisor, desk, telecom and training.

**The trap this vocabulary exists to expose:** a lower cost per minute with a lower conversion rate can raise cost per booking. A cheaper bill is not a cheaper sale.

### 3.6 How they decide who to call

**Rule-based targeting** is what SBI Card does today. Someone writes conditions such as outstanding balance above Rs 20,000 and card vintage over twelve months and no FlexiPay in the last six months, marks that Priority 1, and the whole list gets called, top priority first, at 100 percent coverage.

**Propensity or ML targeting** scores every customer between zero and one on likelihood to convert, and you call in score order. Same effort, more sales, because you stop wasting the first hour on people who were never going to say yes.

Related vocabulary:

- **Pre-approved base.** Customers the bank has already underwritten. No fresh credit check needed. This is what feeds the daily and monthly file.
- **Eligibility.** The risk team's rules on who may be offered what. Separate from propensity, which is about who will say yes.
- **Churn and re-churn cycle.** You keep dialling a number until you reach them or the cycle ends. SBI Card uses 28 days, then the record returns to the pool.
- **ATS, or Average Ticket Size.** The typical transaction or loan value for a customer. The FlexiPay scope targets ATS under Rs 10,000, the low-value tail not worth an agent's time today.
- **Zone segmentation.** The base is split by region. A useful detail, because region is a strong proxy for language, which is how you assign a language to a call without asking the customer.

### 3.7 The compliance vocabulary

This is not paperwork. In Indian financial services it is the thing that kills projects.

- **DNCR or NDNC.** The national Do Not Call Registry. Calling someone on it is a regulatory violation. Every base is scrubbed before dialling.
- **TCCCPR 2018.** TRAI's regulation governing commercial calls: registration, consent, calling hours, complaint handling.
- **RBI outsourcing guidelines.** When a bank hands work to a vendor, the bank remains accountable. This is why there is an InfoSec review before anything is built and why data usually has to stay in India.
- **PII, or Personally Identifiable Information.** Name, card number, address, phone. SBI Card's design deliberately keeps PII out of the calling file. The advisor verifies identity live using billing PIN code and year of birth instead.
- **Consent capture.** A recorded, timestamped, auditable act of agreement. The IVR keypress is the consent artefact.
- **BLC-approved script.** Business, Legal and Compliance have signed off the exact words. An agent may not improvise the terms of a credit offer, and neither may a bot. This is the single biggest constraint on how the AI is built.
- **Mis-selling.** The customer did not understand what they agreed to. Leads to complaints, refunds and regulatory attention. It is the reason a human must stay in the loop for final approval.
- **Audit trail.** An unbroken record across every system the call touched, so a regulator can reconstruct what happened.
- **SR, or Service Request.** The ticket the advisor raises to execute the booking in SBI Card's systems. The point where a yes becomes a transaction.
- **SConnect.** SBI Card's system holding transaction details, used to personalise the pitch and source offer values.
- **C2B link.** The click-to-bank link sent to the customer's registered mobile in the Multicarding journey, opening a prefilled form after OTP.

### 3.8 Voice bot vocabulary

- **ASR or STT.** Speech to text. Quality measured by WER, or Word Error Rate, where lower is better. Indian numbers and code-mixed speech are where it breaks.
- **TTS.** Text to speech. The bot's voice.
- **NLU and intent classification.** Turning "nahi bhai abhi nahi chahiye" into a NOT_INTERESTED label.
- **Barge-in.** The customer interrupts and the bot stops talking immediately. Without it the bot sounds robotic and people hang up.
- **Endpointing and VAD.** Deciding when the customer has finished speaking. Too eager and you cut them off, too patient and the bot feels slow.
- **Latency.** The gap between the customer stopping and the bot starting. Above about one second it feels wrong. Under per-minute billing, latency is literally billed.
- **Containment rate.** Percentage of calls the bot completed without needing a human. In this project a contained call mostly means a rejection the bot handled alone, which is exactly where the savings are.
- **Code-mixing.** Hinglish, Tanglish. Real Indian phone conversations, and the hardest thing for speech models.
- **Cascaded versus speech to speech.** Cascaded converts audio to text, reasons over text, then converts back to audio. Speech to speech maps audio directly to audio with no text layer. Cascaded is slower but every step is inspectable. Speech to speech is faster but harder to prove to a compliance team.

---

## 4. The business problem

### 4.1 The current process, step by step

The three product flowcharts in SBI Card's charter are near-identical for the first eight steps. There is a common data spine before any conversation happens.

1. Analytics or IT team prepares the calling base, segmented by zone, and drops it at a designated path. Daily for FlexiPay and CLIP, monthly for Multicarding.
2. IMAC team encrypts the file with GPG and transfers it via WinSCP to the vendor.
3. The vendor system auto-processes and decrypts the file at server level, per nomenclature rules.
4. Data is uploaded into the vendor dialer through a touchless process.
5. Automated do-not-call scrubbing runs, and the output is shared with the Agency Operations team.
6. MIS Operations receives the scrubbed file, stripped of PII.
7. MIS staff prepare campaign-specific calling files.
8. Calling begins in predictive or progressive mode depending on volume.

Then the human call. The advisor verifies the customer using billing address, PIN code and year of birth. They pitch the offer against SConnect transaction details. They gauge interest. If interested, they walk the customer through a secured IVR where pressing one accepts, then submit the SR, which auto-creates in SBI Card's systems. If uncontactable, the record is re-churned for a fresh attempt after the 28-day cycle ends.

**Steps one to eight do not change.** That pipeline is already automated and touchless. The entire opportunity lives in step nine onwards.

### 4.2 The three products in Phase 1

| Product | Base | Stated target |
|---|---|---|
| FlexiPay | Unused dataset of eligible ATS under Rs 10,000 | Increase revenue |
| Multicarding | Complete dataset | Reduce cost |
| CLIP | Complete dataset | Reduce cost |

Note the asymmetry, because it is the most useful thing on that slide and it is easy to skim past.

FlexiPay is pointed at a low-ticket segment humans currently do not call at all. The bot creates incremental revenue on calls that would otherwise never happen. Multicarding and CLIP are the full existing base, so the bot substitutes for human minutes and has to be cheaper per outcome.

Two different success metrics. Pitching one number for all three misses the point entirely.

### 4.3 Where it strains today

From SBI Card's own problem statement in the process flows deck:

- **Advisor time burnt on the repetitive front-end.** Verify, pitch, FAQs and interest check happen on every call, before any sale is known.
- **Reach capped by manpower.** Large calling bases re-churned across 28-day cycles, and scaling means adding seats to a 2,000-plus seat operation.
- **Inconsistent pitch and compliance.** Script, tone and consent capture vary advisor to advisor.
- **High cost per contacted minute.** Human effort spent on low-converting segments, for example the unused FlexiPay base under Rs 10,000 ATS.

### 4.4 What SBI Card wants to achieve

Also from their own deck:

- AI BOT owns the front-end, using the approved script and the FAQ glossary, capturing interest and consent, then transferring to an advisor. IVR, SR and C2B journeys stay unchanged.
- Lower cost with the same or better conversion. Advisors spend time only on interested customers.
- Cover the full eligible base. Thousands of parallel calls, full availability in calling hours, multilingual reach.
- Compliance by design. Consent recordings, no PII in the base, audit trail across bot, dialer, CRM and SBI Card systems.

### 4.5 The problem underneath the stated problem

Stated: build a multilingual outbound voice bot.

Actual: **prove that replacing sixty to ninety seconds of scripted human pitch with a bot lowers total cost per booked SR, across nine Indian languages, without breaking a compliance chain that currently has a human on every consent, while integrating into someone else's dialer, under someone else's contract, judged against two competitors on the same base.**

The voice bot is table stakes. The economics, the integration and the analytics wrapped around the calls are what decide it.

---

## 5. What is actually being sold

### 5.1 The wedge

Every call has two halves.

**The first ninety seconds.** Greet, detect language, soft identity check, pitch the offer, answer FAQs and objections, check interest. Repeatable, and none of it is a decision.

**Everything after.** Verify identity properly, run the consent IVR, fill the form, raise the SR. Legally sensitive, and a human must do it.

We replace only the first half. That is the whole project. Think of it as replacing the person handing out flyers at the mall entrance, not the person at the billing counter.

### 5.2 What changes, per product

The bot's job is narrow and near-identical across all three: answer, pitch from an approved script, probe against an FAQ set, detect agreement, then hand off or dispose. What differs is what happens after the yes.

**FlexiPay.** Bot answers, uses the approved script with dynamic variables, probes using SBI Card-approved FAQs. A gate on the sub-Rs 10,000 segment routes eligible calls to the bot. If the customer agrees, verification happens, then the **advisor** takes over and runs the secured IVR, then submits the SR. If not, the bot disposes as not interested. Note that the IVR is advisor-run here, not bot-run.

**Multicarding.** Bot pitches and probes per approved FAQs. If the customer agrees, the **advisor** verifies identity, fills the multicarding form and triggers a C2B link to the registered mobile. The customer clicks, submits OTP, and completes a prefilled form. **There is no IVR journey at all.**

**CLIP.** Bot answers, pitches the offer using approved script and file details, probes per SBI Card FAQs. If the customer agrees, the call transfers to the advisor and the **secured IVR journey runs with the bot**. On acceptance, the advisor submits the SR. If the bot fails to gain agreement, the advisor disposes the call in the partner CRM based on the previous interaction.

### 5.3 The guardrails, non-negotiable

- **Script, not improvisation.** The BLC script is a state machine. The model may only paraphrase inside a node.
- **Offers are read, not written.** Amounts and terms come from SConnect variables and are never generated.
- **A human makes every decision.** Verification, consent and booking stay with the advisor.
- **Safe exit on any turn.** A do-not-call request, abuse or repeated silence ends the call and flags the record.
- **Audit trail end to end.** Every turn, consent event and disposition logged across bot, dialer and CRM.

### 5.4 The seven capabilities they are actually buying

SBI Card's charter lists seven components under "Project Scope: AI Voice Platform Features". Only the first is the voice bot.

1. **Outbound AI voice agents**, specialised per CLIP, Multicarding and FlexiPay workflow
2. **Sentiment analysis**, extracting sentiment, trends and behavioural insight from call interactions
3. **Best time to call analysis**, optimising calling windows from historical metadata to lift connect rates
4. **Intelligence cuts**, meaning dashboards tracking conversion metrics and contact attempts
5. **Speech-to-text quality audit**, evaluating transcription accuracy and managing a secure three-year archive of all call text
6. **Successful bot call repository**, archiving winning automated interactions for quality assurance, compliance and training
7. **Languages covered**, multilingual support across the required set

Items two through five are analytics and MLOps, not speech engineering. Given that competing vendors are flagged as stronger on voice specifically, this list is where the case is winnable.

---

## 6. The economics

This is the section that decides the deal. Everything else is supporting material.

### 6.1 The uncomfortable finding

The benchmark on the table is Rs 9 per contacted minute, Rs 2.76 crore a month.

Now price the human being that bot is replacing. A fully loaded domestic outbound BFSI seat in India costs roughly Rs 25,000 to Rs 32,000 a month once you include salary, incentive, supervision, infrastructure, telecom, attrition and training overhead. An agent on a predictive dialer logs about eight hours and spends thirty to forty-five percent of it in actual talk time.

At Rs 28,000 a month and thirty-five percent talk-time utilisation over twenty-six days, that works out to roughly **Rs 6.40 per contacted minute**. At forty-five percent utilisation it drops to about Rs 5.

**So the proposal, framed naively, is: replace a Rs 6.40 human with a Rs 9 robot.** Indian domestic telecalling labour is genuinely cheap, and any pitch built on "AI is cheaper than agents" collapses the moment someone at SBI Card does that arithmetic. Given cost reduction is their stated design constraint, they will.

All of those figures are our estimates, not SBI Card's, and they must be replaced with their actuals in week one of any POC. But the shape holds.

### 6.2 The right denominator

Cost per minute is the wrong unit. The right one is cost per booked SR.

```
cost per booking = cost per contact / (agreement rate x consent-to-booking rate)
```

Which gives one clean decision rule:

> **The bot's conversion, relative to a human, must not fall below its cost relative to a human.**

If the bot costs eighty percent of an advisor per contact but converts thirty percent worse, cost per booking rises fourteen percent. The invoice looks smaller and the sale costs more.

### 6.3 The fifty-second rule

The bot does not replace the whole call. It replaces the pitch and probe, roughly the first ninety seconds. So the comparison is bot minutes for the pitch versus advisor minutes for the same pitch.

At Rs 9 a minute for the bot and Rs 6.40 for the advisor, on a ninety-second human pitch:

```
9 x (t/60) = 6.40 x 1.5    gives    t = 64 seconds
```

Allow for slightly worse conversion and it falls to about fifty-four seconds. At an assumed Rs 5 advisor cost it is fifty seconds.

**The bot must complete pitch, probe and objection handling in well under a minute or it costs more than the human it replaced.** This explains exactly why SBI Card chose per-contacted-minute pricing. It forces the vendor to be terse and transfers the latency risk to the vendor.

### 6.4 The illustrative comparison

Take 100 people who actually pick up. Roughly 88 say no, about 12 say yes. The advisor spends ninety seconds on all 100, because you cannot know who will say yes until you pitch.

| | Human advisor | Bot at Rs 9 a minute, 60-second pitch |
|---|---|---|
| Cost for 100 contacts | 100 x 1.5 min x Rs 6.40 = Rs 960 | 100 x 1 min x Rs 9 = Rs 900 |
| Customers who agree | 12 | About 10 |
| **Cost per agreement** | **Rs 80** | **Rs 88** |

The invoice looks six percent smaller. The cost of actually selling something is ten percent higher. That is the sentence to lead with in any internal conversation.

### 6.5 Where the savings genuinely are

Since per-minute arbitrage is weak, the case rests on four things the per-minute rate does not capture.

**1. Talk-time compression on the rejection mass.** Roughly 85 to 90 percent of contacts end in not interested. A human spends the full ninety seconds discovering that. A well-tuned bot can discover it in twenty-five to thirty-five. Savings concentrate almost entirely here, which means the optimisation target is **time to disqualify**, not time to sell.

**2. Coverage without headcount.** The FlexiPay sub-Rs 10,000 segment is uncalled today because it is not worth an agent's time. Every booking there is incremental revenue against a base of zero. It is the cleanest number in the deal and it is not a cost saving at all, it is new topline.

**3. Shrinkage, attrition and ramp.** Domestic outbound telecalling in India runs sixty to eighty percent annual attrition. Every seat carries hiring, two to three weeks of training, ramp to productivity, supervision ratios of roughly one to fifteen, and QA sampling. A per-minute comparison silently gives the human side all of that for free.

**4. Connect-rate lift from best-time-to-call.** The underrated one. Improving connect rate does not reduce cost per minute, it reduces wasted dial attempts, which multiplies through the entire funnel. A fifteen percent connect-rate lift improves cost per booking by roughly thirteen percent at zero marginal cost. It is a supervised learning problem on data SBI Card already has, and it is squarely TransOrg's home turf rather than a voice vendor's.

### 6.6 Our cost build-up

Direct model and infrastructure cost per contacted minute, assuming the bot speaks about forty-five percent of it, at published India-hosted list prices as at September 2026:

| Component | Basis | Per contacted minute |
|---|---|---|
| Text to speech | Rs 30 per 10,000 characters, about 370 characters a minute | Rs 1.10 |
| Speech to text | Rs 30 to 45 per hour of audio | Rs 0.60 |
| Orchestration and infrastructure | Self-hosted, about 1,000 concurrent sessions | Rs 0.50 |
| Reasoning model | Small model, cached script prompt | Rs 0.25 |
| Recording, QA sampling and analytics | Including the three-year archive | Rs 0.25 |
| Telephony | The partner's SIP trunk, no new carrier | Rs 0.00 |
| **Direct AI cost** | | **Rs 2.70** |

Now the fixed base the direct cost ignores. A realistic run team is six engineers, three QA auditors, one operations lead and a fractional data scientist, at roughly Rs 2.8 crore a year fully loaded. Add build amortisation of about Rs 2 crore over twenty-four months, plus monitoring, staging, disaster recovery, security tooling and the archive. That is around **Rs 35 lakh a month in fixed cost**.

At Phase-1 volume that adds about Rs 1.14 per minute.

> **Fully loaded cost is roughly Rs 3.85 per contacted minute at scale.** At the fifty-second target that is about **Rs 3.96 per contacted conversation** once fixed cost is loaded per conversation.

That figure is the floor under every price below. It is also the number most exposed to being wrong, because the Rs 35 lakh fixed base is an estimate rather than a costed plan.

### 6.7 The two levers

**Lever 1: a cheaper minute.** This is what the POC gets priced on. It is arithmetic on published list prices, shown above. The remaining Rs 3.80 to 4.30 above the Rs 2.70 direct cost covers build amortisation, script and language tuning, round-the-clock operations, the QA audit team, the three-year archive and margin. That is how an all-in Rs 6.5 to 7 holds against a Rs 9 quote.

**Lever 2: fewer minutes worth buying at all.** This is the Phase-2 upside and it is the reason to pick an analytics partner rather than a voice vendor. Today the full eligible base is dialled on priority 1 and 2 rules. A cheaper minute applied to the same coverage only lowers the rate. Scoring the base changes how many minutes are bought.

Three mechanisms:

- **Propensity to convert.** A scored ranking per product replaces the rule set. Low-propensity records move to fewer attempts or a cheaper channel.
- **Best time to call.** Connect and conversion by hour, day and zone, drawn from dialer and bot logs, sets the calling windows.
- **Attempt policy.** How many retries a number is worth before the 28-day re-churn. Most of the waste sits in attempts, not first calls.

Because billing is per contacted minute, every ten percent of wasted attempts retired is ten percent off the bill on top of the lower rate. We size this from the POC's own data and promise no figure in advance.

**Neither lever is a claim about better speech. That is deliberate.**

### 6.8 The billing-unit trap

This is the most important unresolved point in the whole economic analysis, and it has not yet made it into any deck.

We are engineering the bot to finish in fifty seconds instead of ninety. That is our entire efficiency story. But under per-minute billing, shorter calls shrink our own revenue while our fixed costs stay exactly where they are.

At the same coverage of 20.5 lakh contacted conversations a month:

| | Talk time | Billed minutes | Our revenue at Rs 6.75 |
|---|---|---|---|
| If we talk 90 seconds | 1.50 min | 30.7 lakh | Rs 2.07 Cr |
| If we talk 50 seconds | 0.83 min | 17.1 lakh | Rs 1.15 Cr |

We do the harder engineering and get paid forty-four percent less for it. Per-minute pricing rewards padding the call, which is exactly the behaviour SBI Card should not want and exactly what a Rs 9 per minute quote quietly encourages.

**Recommendation: price per contacted conversation, not per contacted minute.** That removes our incentive to drag calls out, removes the client's fear that we will, makes our efficiency a shared gain rather than a self-inflicted revenue cut, and makes direct rate comparison against unfyd harder in a way that favours us.


---

## 7. The competitive field

Five rivals, researched from public sources in September 2026. All capability claims below are drawn from vendor positioning and are unverified. Only unfyd.AI's price is known, and it comes from SBI Card's own charter.

### 7.1 The thing that explains everything else

These five are not five versions of the same company. They are three different business models, and the model predicts the architecture, the price and the pitch.

- **Model builders**, meaning Gnani.ai, own the speech and language models themselves. They compete on accuracy and latency, and they sell on-premise deployment.
- **Workflow specialists**, meaning Skit.ai, own a business process end to end. The bot is one step in it. They compete on outcomes and often price on outcomes.
- **Platform overlays**, meaning unfyd.AI, DialNexa and Yellow.ai, sit on top of existing telephony and CRM and assemble models from elsewhere. They compete on breadth and speed of deployment.

### 7.2 unfyd.AI

Run by SmartConnect Technologies, Mumbai. The quote already on SBI Card's table.

**How they work.** A CX platform first, a voice bot second. Their product suite is a long list of modules: UNFYD.CX, UNFYD.CRM, UNFYD.BOT, UNFYD.SCOR, UNFYD.INSIGHT, UNFYD.AI, plus unified communications tooling. The bot is one module inside an omnichannel stack that also handles chat, WhatsApp, social, agent desktop and workforce engagement. Their sentiment and journey scoring product, UNFYD.SCOR, is driven by UNFYD.AI and analyses interactions for sentiment and 360-degree data analytics. Architecturally this is a conventional cascaded pipeline.

**Their cost.** Rs 9.00 per contacted minute, roughly Rs 2.76 crore a month at Phase-1 volume. Worth noting what Rs 9 is in world terms: about ten US cents, which puts them in the same band as globally bundled voice platforms that embed speech, language model, text to speech and telephony in one rate at $0.11 to $0.14 a minute with an estimated fifteen to forty percent markup on components. So they are priced like a Western bundled vendor while sitting at the top of the Indian band of Rs 2 to 12.

**Where the LLM sits.** Two places. Inside the bot module for conversation, and inside UNFYD.SCOR for sentiment and interaction analytics after the call. They do not publish which models, which usually means third-party models under the hood.

**What they would propose.** Almost certainly what they already have. SBI Card's seven-point requirement list reads like a product sheet, and it is worth assuming it was written with one vendor's capabilities in view. Their pitch is that you get the whole CX platform and the bot comes with it.

**Their weakness.** Breadth, not depth. Nothing in their positioning suggests telephony-grade Indic speech engineering, and Rs 9 is hard to defend once a buyer sees the market band.

### 7.3 DialNexa

Bengaluru-built. The most architecturally honest of the five.

**How they work.** They describe their own design as three layers, and it is the cleanest mental model in this space. A telephony layer that places and receives calls. A conversation layer that manages intent, scripts, qualification logic and dispositions. A system-of-record layer, the CRM, where ownership, follow-up tasks, notes and pipeline status live. The design philosophy is to be an overlay: it runs on top of your existing telephony providers, CRMs and ticketing systems, so nothing has to be ripped out. On the call itself the agent picks up instantly, holds a natural conversation, follows your scripts, keeps context across the call and hands off to a human when it should. The customer controls the voice, scripts, guardrails and escalation rules. Multilingual coverage includes Hindi, Kannada, Tamil and Telugu, and they build for ultra-low latency and high concurrency.

**Their cost.** Not published. Given their positioning as an India-native overlay with no model R&D to amortise, expect a bid in the Rs 3 to 6 mid-market band, which would undercut both unfyd and us.

**Where the LLM sits.** Entirely in the conversation layer, handling intent, qualification logic and disposition tagging. They do not name their models, which again suggests third-party. Their engineering blog runs long-form pieces on voice AI architecture, latency and telephony infrastructure, so there is real engineering there, but the models are almost certainly bought rather than built.

**What they would propose.** Their pitch writes itself against SBI Card's constraint. SBI Card explicitly wants this running through the existing dialer vendor rather than as a standalone hosted platform, and DialNexa's entire product is "we sit on top of what you already have." They would plug into the partner's dialer and CRM with no infrastructure change, build separate agents for CLIP, Multicarding and FlexiPay, and report connect rate, handling time, conversion and drop-off points.

**Their weakness, and the real threat.** They are small, with eighteen customer reviews on Trustpilot, and nobody has pushed thirty lakh minutes a month through them. But they offer white-label to agencies, which means SBI Card's calling partner could resell DialNexa under their own name and the bake-off never happens. That is a route-to-market risk rather than a product risk, and it is the one worth raising with Shrey.

### 7.4 Gnani.ai

The one that should worry us on technology.

**How they work.** They build their own models end to end. The full stack of speech to text, text to speech and language models is developed in-house with no dependency on third-party model providers, trained on over fourteen million hours of real telephonic audio. That last point is the whole game: most speech models are trained on clean studio audio, while enterprise voice involves background noise, regional accents and code-switching, and they rank first on eight of nine Indian languages on the Kathbath Noisy 8 kHz benchmark. On a call they detect the spoken language at the start with no manual selection, recognise speech mid-sentence without waiting for silence, and handle a customer switching from Hindi to English or Tamil to English mid-call.

Their newest architecture removes the text layer entirely. It is a five-billion-parameter model going speech to speech directly, with no speech-to-text, no text-to-speech and no intermediate text layer, at a claimed sub-200 millisecond P95. Their text to speech separately claims sub-100 millisecond time to first audio across twenty-one or more languages.

**Their cost.** Not published, enterprise quote only. They claim enterprises typically see a sixty percent reduction in contact centre operating expenditure. Full-stack ownership means their marginal cost per minute is structurally lower than anyone renting models, so they can go low if they choose to.

**Where the LLM sits.** Everywhere, and it is theirs. Aion is a tool-calling agentic model purpose-built for Indic languages, delivering multi-turn reasoning and tool orchestration across eleven or more Indic languages, running on-premise and at the edge. In the speech-to-speech model there is no separate LLM step at all, because the model is the whole pipeline.

**What they would propose.** On-premise or air-gapped deployment inside SBI Card's or the partner's infrastructure, their own models throughout, benchmarked language accuracy as the headline, and compliance as the closer. They support cloud, private cloud, on-premise and air-gapped deployment, meeting data residency requirements for banking under RBI, insurance under IRDAI and healthcare, and they hold SOC 2 and ISO 27001 with GDPR, HIPAA and PCI-DSS compliance across more than 200 enterprise deployments.

**Their weakness.** They sell a voice bot, extremely well. They do not sell a model of which customers to call, when, or how many attempts are worth buying. That is the only gap, and it is the one we should stand in.

### 7.5 Skit.ai

Not a voice bot company that does collections. A collections company that talks.

**How they work.** Founded in 2016, voice-first from the start. Today it is an omnichannel platform across voice, SMS, email and chat, and the voice agent is one actor inside a larger workflow engine. The platform routes accounts to the right agent, runs approval workflows for strategy and settlements, and escalates stalled cases to humans. Critically, it scores propensity to pay on every account and recalibrates segments and offers as new signals come in, and it reviews every conversation against FDCPA, TCPA and state rules. Compliance is described as part of the core architecture rather than an add-on. Deployment is fast: with minor bot configuration and file sharing they claim to go live in under two days.

**Their cost.** The interesting one. They offer risk-free, contingency-based, outcome-based pricing where they are paid only if the client wins. No per-minute rate at all.

**Where the LLM sits.** In the conversation, obviously, but also in two places nobody else uses it. In compliance, reviewing every conversation against the rulebook automatically. And alongside classical machine learning in the targeting layer, scoring propensity and running smart retry strategies.

**What they would propose.** They would not compete on cost per minute. They would offer to be paid on booked SRs, run their own targeting model over SBI Card's base, and go live in days rather than weeks. For a client whose stated constraint is that efficiency must translate into real cost reduction, being paid only on results is an extremely strong answer.

**Their weakness for this deal.** Their depth is collections, not cross-sell. Propensity to pay on a delinquent account is a different modelling problem from propensity to convert on a FlexiPay offer. Their Indian language depth is real but less benchmarked than Gnani's.

### 7.6 Yellow.ai

The biggest name and the broadest platform.

**How they work.** Two products matter here. Orchestrator LLM is their in-house fine-tuned model that identifies multiple intents, retains context across a conversation and directs users toward the primary goal with zero training or complex setup. VoiceX is the voice layer, positioned as low-latency human-like agents for IVR replacement, outbound and verification. Around them sits a drag-and-drop bot builder with flow diagrams and Node.js scripting, agentic retrieval to ground answers in your own knowledge base, and 150 or more integrations into CRMs, contact centre platforms and help desks, spanning 35 or more channels and 135 or more languages.

**Their cost.** Quote-based, with no public list prices or tiers. Independent reviewers flag opaque custom pricing and implementation weight as the main drawbacks. Expect a platform licence plus usage plus a services line, which is exactly the structure that makes cost per booked SR hard to compute.

**Where the LLM sits.** Three layers, deliberately. Their own Orchestrator LLM for conversation orchestration, multi-LLM flexibility across fifteen or more third-party models for generation, and their proprietary DynamicNLP engine for intent. Answers are grounded through agentic retrieval against your knowledge base rather than generated freely.

**What they would propose.** A full conversational AI platform, not just an outbound bot. The cross-sell bot as phase one, with inbound service, WhatsApp and agent assist as the roadmap. Classic land and expand.

**Their weakness.** Horizontal by design. Card cross-sell economics is one vertical among dozens, and opaque pricing is a liability against a client whose explicit design constraint is provable cost reduction.

### 7.7 Price comparison

| Vendor | What they charge | Structure |
|---|---|---|
| unfyd.AI | Rs 9.00 per contacted minute | Bundled, quoted in the charter |
| DialNexa | Not published | Likely per-minute, mid-market band |
| Gnani.ai | Not published | Enterprise quote, on-premise licence likely |
| Skit.ai | Contingency, paid on results | Outcome-based |
| Yellow.ai | Not published | Platform plus usage plus services |
| **TransOrg** | **See section 8** | **Per conversation, floor plus performance share** |

For context, published Indian voice AI rates run Rs 2 to 12 per minute with Rs 3 to 6 the common mid-market band. Globally, pure orchestration platforms charge around $0.01 a minute and pass model costs through, mid-market platforms layer $0.05 to $0.09, and fully bundled platforms sit at $0.11 to $0.14.

### 7.8 What none of them sell

Gnani sells a better call. DialNexa sells easier plumbing. Yellow sells a bigger platform. unfyd sells a CX suite. Skit is the only one with a targeting model, and theirs is built for collections, not cross-sell.

The line that survives contact with all five is narrow and specific: **we are the only bidder proposing to model propensity to convert on SBI Card's own cross-sell history, and to prove it against a human control arm.**

---

## 8. Our approach and positioning

### 8.1 The box we are in

Three things follow honestly from the competitive picture.

**We cannot win a rate auction.** Gnani owns its model stack, so their marginal cost is structurally lower. DialNexa is a lean overlay with no model R&D to amortise. If SBI Card runs this as a lowest-rate bake-off, we come third.

**We cannot win on speech.** Gnani is measurably better on Indic telephony audio and everyone in the room will hear it.

**Skit's commercial structure is more persuasive than any rate.** Being paid only on results answers SBI Card's stated constraint better than any number we can quote.

So the answer cannot be a cheaper version of what everyone else is selling.

### 8.2 The recommended offer

> **Rs 4.75 per contacted conversation as a floor, plus twenty-five percent of the verified reduction in cost per booked SR against a human control arm, with the blended rate capped at Rs 6.50 per conversation.**

**The floor of Rs 4.75** covers our Rs 3.96 fully loaded cost with a seventeen percent margin. We never lose money even if the bot underperforms badly. This is the number procurement anchors on.

**The performance share** beats Skit at their own game without taking their risk. The advisor-only baseline is about Rs 80 per agreement. At our floor rate with an eleven percent agreement rate we deliver an agreement for about Rs 43. That is a saving of roughly Rs 37 per agreement, and across 2.26 lakh agreements a month it is about Rs 83 lakh of monthly saving. Our twenty-five percent share is around Rs 21 lakh a month, or about Rs 1.02 per conversation.

**The cap at Rs 6.50** means SBI Card knows their worst case before they sign.

**Blended outcome if we hit our numbers: about Rs 5.77 per contacted conversation.** At the fifty-second target that is roughly Rs 6.90 per contacted minute equivalent, which sits inside the Rs 6.5 to 7 band already agreed internally.

At Phase-1 coverage that is roughly **Rs 1.18 crore a month, or Rs 14.2 crore a year, against unfyd's Rs 33 crore.** SBI Card saves close to Rs 19 crore a year against the quote in front of them. Our margin at that blend is about thirty-one percent, and seventeen percent at the floor alone.

### 8.3 Sensitivity

| Scenario | Effect |
|---|---|
| DialNexa bids Rs 5 per minute | Their cost per agreement lands near Rs 48, roughly level with ours. A rate war ends in a tie, not a win. |
| POC volume is small | Fixed cost dominates. At three lakh conversations a month our unit cost is around Rs 14, so the POC is loss-making at any sane price. |
| Bot agreement rate falls below eight percent | Cost per booked SR rises above the advisor baseline, the performance share goes to zero, and we earn the floor only. |
| SBI Card insists on per-minute quoting | Fall back to Rs 6.60 per contacted minute with a written commitment that average talk time stays under fifty-five seconds. |

Expect to spend roughly **Rs 18 to 25 lakh** over three months to win this. Against a Rs 14 crore annual contract that is a payback of under one month of production revenue.

### 8.4 Target area: lead with FlexiPay, not CLIP

We originally planned to lead the POC with CLIP. That is the wrong choice, and the reasoning matters.

**CLIP is the worst possible ground for us.** It is the full base, worked today by humans, with a working baseline. Winning there means beating a human process on conversion, judged against a control arm, in a head-to-head where Gnani's better speech directly improves their number and ours stays flat. Every competitor will pitch CLIP because it is the biggest base. We would be fighting five rivals on the one battlefield where our weakness matters most.

**FlexiPay's sub-Rs 10,000 ticket-size base is the right ground.** That segment gets no calls today because it is not worth an advisor's time. Revenue from it is currently zero.

Four reasons that changes everything:

- **There is no baseline to lose against.** Cost per booked SR cannot be worse than a human, because no human is calling. The comparison that would sink us does not exist.
- **It is a revenue story, not a cost story.** Every booking is new topline, which is a much easier conversation with a CFO than arguing about seat costs.
- **Propensity scoring is the deciding capability there, not speech quality.** At a sub-Rs 10,000 ticket size, whether a call is worth making at all depends entirely on targeting precision. That is the one row on the comparison matrix where we stand alone.
- **Nobody else will pitch it.** Every rival will lead with the biggest base.

**Recommendation: lead with FlexiPay sub-Rs 10,000 in the POC, add CLIP in phase two once the cost-per-booking machinery is proven.** Same four-week build, different base file.

### 8.5 Where not to fight

Do not fight Gnani on speech quality. Do not fight DialNexa on integration simplicity. Do not fight Yellow on platform breadth. Fight on who to call, when, how many attempts are worth buying, and provable cost per booked SR against a control arm.

### 8.6 The three sentences for the room

> We charge per conversation, not per minute, because per-minute billing pays a vendor to keep talking.
>
> Our floor is Rs 4.75 a conversation and we only earn more if cost per booked SR actually falls, measured against your own advisors on the same base.
>
> We want to start on the FlexiPay base you are not calling today, because that is where a targeting model is worth more than a better voice.


---

## 9. Technical architecture

### 9.1 High level design: three zones

**Zone 1, SBI Card, unchanged.**

- Calling base: priority 1 and 2 rules, GPG encrypted, WinSCP to the vendor
- SBI Card systems: SR created when the advisor submits it
- Scripts and offers: BLC scripts, SConnect variables, FAQ glossary

**Zone 2, the dialer partner, two hooks.**

- Predictive dialer: upload, do-not-call scrub, retries, routes answered legs to us
- Advisor idle pool: verify, take consent, raise the SR
- Partner CRM: campaign records, dispositions, consent events

**Zone 3, the TransOrg voice layer, new.**

- Media gateway: answers the SIP leg, audio in and out, recording tap
- Orchestrator: runs the script as a state machine, handles end-of-turn detection, barge-in and mid-call language switching
- Speech to text: Indic, streaming, code-mix aware
- Reasoning model: paraphrases inside the current node only
- Text to speech: Indic, streaming, nine voices
- Script store: versioned per journey
- Call database: turns, dispositions, consent events
- Recording store: encrypted, three-year retention
- Dashboards: attempts, transfers, SRs, rate per minute

**Hook 1: SIP trunk and RTP audio.** The dialer routes an answered call to us. We answer the leg, stream audio both ways, then hand the call back by SIP REFER with a whisper summary for the advisor.

**Hook 2: CRM API over mutual TLS.** We write the disposition, the consent event and a masked reference id back to the partner CRM. Nothing is written into SBI Card's own systems by us.

**Governance across all zones.** Mutual-TLS APIs, no PII in the calling base with a masked reference id instead, key vault, immutable audit log, India-hosted speech models, and no automated approvals since every SR is raised by an advisor.

### 9.2 Low level design: one turn of conversation

Target under one second from the customer falling silent to the bot making a sound.

| Step | What happens | Budget |
|---|---|---|
| 1. Customer stops speaking | 8 kHz audio arriving from the SIP leg | |
| 2. End-of-turn detection | Decides they have finished, not just paused | 150 ms |
| 3. Speech to text | Streams while they talk, so this is the tail only | 250 ms |
| 4. Script node plus model | Classifies intent, picks the next node, paraphrases inside it | 300 ms |
| 5. Text to speech | Time to the first byte of audio, then it streams | 200 ms |
| 6. Bot audio out | Total, end of speech to first sound | **0.9 s** |

Note that end-of-turn detection eats a large share of the budget, which surprises people who assume the model is the bottleneck. And because most turns play a pre-recorded line rather than generating speech, the text-to-speech figure stays realistic on Indic voices.

### 9.3 Why cascaded rather than speech to speech

Three reasons, all compliance-driven.

- The script must stay BLC-approved. A model cannot improvise the terms of a credit offer. A cascaded pipeline lets the script spine be fixed text or pre-recorded audio.
- We owe a three-year transcript archive and a speech-to-text quality audit. A cascaded pipeline produces that as a by-product. Speech to speech makes it a bolt-on.
- Indic support in end-to-end speech models is materially weaker than in dedicated Indic speech models, with the notable exception of Gnani's own.

The latency advantage of speech to speech is real, and Gnani has it. We accept that trade deliberately rather than pretending it does not exist.

### 9.4 What one script node contains

- **Spoken line.** A human recording per language. The model may only paraphrase inside it.
- **Variables.** Offer amount, tenure, name, read from SConnect. Never generated.
- **Allowed intents.** The seven labels this node accepts, and where each one goes next.
- **Guardrail.** What it may not say here, and the fallback line if the customer goes off script.
- **Timeout.** How long to wait, and the re-prompt if the customer says nothing.

### 9.5 The interfaces

| Interface | Protocol and payload |
|---|---|
| Base in | GPG file over SFTP. Masked reference id and offer variables only |
| Call in | SIP INVITE from the partner dialer, RTP audio at 8 kHz |
| Call out | SIP REFER to the advisor pool, with a whisper summary |
| Write back | CRM API over mutual TLS: disposition, consent event, recording pointer |

### 9.6 Failure handling

| Situation | Behaviour |
|---|---|
| Cannot understand | Re-prompt once, hand to a human on the third failure |
| Silence | Two re-prompts, then dispose the call and flag for re-churn |
| Off script | The node's fallback line, never an improvised answer |
| Stop request or abuse | End the call immediately and flag the record |

### 9.7 Language strategy

**The nine languages, per Shrey's email**, which is the authoritative source: English, Hindi, four South Indian languages meaning Tamil, Telugu, Kannada and Malayalam, plus Marathi, Gujarati and Bengali.

The hard parts are not the count.

- **Code-mixing.** Real Indian phone conversations are Hinglish, Tanglish, Kanglish. A monolingual Hindi model degrades badly on "mera limit increase kar do". We need code-switching-tolerant models, not nine clean monolingual ones.
- **Numbers and money.** The single biggest failure mode in Indian BFSI voice. "Pachaas hazaar", "fifty thousand", "50K" and "point five lakh" all mean the same thing and all break naive transcription. A domain lexicon and numeric normaliser come before anything else.
- **Language assignment.** Do not make customers press a key. The base is already zone-segmented, so assign a probable language from region, then run runtime language detection on the first customer utterance and switch if wrong. Log the switch rate as a quality metric.
- **Per-language evaluation.** Report word error rate, intent accuracy and agreement rate separately per language. Malayalam, Kannada and Marathi typically lag Hindi by a wide margin, and an aggregate number hides that.

**Rollout order.** Hindi and English deep first, then Tamil and Telugu, then the remainder. Nine shallow languages will lose to two that work.

**Model sourcing.** India-hosted Indic speech models. We will not beat the specialists by training from scratch and should not try. The differentiation is orchestration and analytics, not speech.

### 9.8 Security and deployment

Assume this ends up deployed inside the calling partner's infrastructure or an India-region private cloud, not as an API call to a foreign endpoint. RBI outsourcing guidelines and data-localisation expectations push hard in that direction, and an InfoSec review gates implementation.

Practical consequences to plan for now, not later:

- Model inference must be India-resident. That means self-hosted open-weight models or India-region managed endpoints, which changes both the cost stack and the latency numbers.
- The bot receives a masked reference id and offer parameters, not card numbers. Identity verification stays with the advisor, which conveniently keeps PII out of our system entirely.
- Encryption in transit and at rest, GPG for file exchange to match the existing pattern, immutable audit log, three-year retention for transcripts and consent recordings.
- TCCCPR 2018 obligations around do-not-call and unsolicited commercial communication apply to the dialling. The partner owns that, but confirm it in writing.

---

## 10. Build roadmap

Four weeks to a product that makes real calls. Four workstreams in parallel, one gate at the end.

### Week 1

- **Integration.** Test SIP line up. Bot dials out, hears audio, tells a person from a voicemail.
- **Conversation.** Bake-off of speech-to-text engines on real card audio, scored on Hindi, Hinglish and spoken amounts.
- **Data.** Event schema and call database designed. Every turn of every call gets a row.
- **Compliance.** Masked reference id design, key vault, no PII anywhere in our store.

### Week 2

- **Integration.** Live handover to a free advisor, with a whisper summary played to them first.
- **Conversation.** Approved script becomes a configuration file. Human recordings for every fixed line.
- **Data.** Turn logging live end to end, including consent events and dispositions.
- **Compliance.** Consent recordings stored as evidence, audit log locked against edits.

### Week 3

- **Integration.** Write-back to the partner CRM over mutual TLS: outcome, consent, recording pointer.
- **Conversation.** FAQ answers grounded to the glossary, two objection loops, barge-in and mid-call language switch.
- **Data.** Funnel and cost-per-sale dashboards, measured against the advisor-only baseline.
- **Compliance.** Three-year archive in place with QA sampling running against it.

### Week 4

- **Integration.** Daily encrypted file ingested. Duplicates and do-not-call numbers removed, attempts tracked.
- **Conversation.** All nine language voices in, plus a sampled check that the bot stays on script.
- **Data.** First when-to-call model on historical connect data, plus the propensity feature set.
- **Compliance.** India-hosting proof, load test at 1,000 concurrent calls, InfoSec pack submitted.

### The Day 30 gate

| Criterion | Target |
|---|---|
| Live call | Hindi and English, under one second a turn |
| Full journey | File in to SR out |
| Script adherence | Ninety-eight percent on sampled QA |
| Rate | Demonstrated at Rs 7.0 or below |
| InfoSec | Pack submitted |

The sequencing is deliberate. Week 1 de-risks the stack, because latency and word error rate on Hinglish are the two things that can kill the economic case, and finding that out in week one is cheap while finding it out in week nine is not.

Language coverage beyond Hindi and English, and the remaining journeys, are added during the live POC that follows the gate.

### The longer POC

SBI Card's evaluation runs three months with three partners. The build above is the first month of that. The remainder is the live run with a human control arm on the same base, weekly script iteration from the successful-call repository, and the best-time-to-call model switched on once there is enough data.

**The output that wins this is not a working bot. It is a defensible cost-per-booking number with a human control group standing next to it.**

---

## 11. What we have produced so far

Three artefacts exist. Two are client-facing, one is not.

### 11.1 The approach note, six slides, dated 8 September 2026

**Status: delivered.** This is deliverable one from Shrey's list, and its subtitle mirrors his three-item brief word for word: voice bot layer, multilingual handling, human handoff.

1. **Title.** TransOrg by SBI Card. "The bot qualifies. Your advisor closes. Cost per booking falls."
2. **How outbound cross-sell runs today.** The six-step calling chain, where a contacted minute goes, and where the cost sits. Establishes that roughly sixty percent of talk time comes before a yes.
3. **What we build: the call, split at intent.** One call, two lanes, seven numbered steps split between the AI voice agent and the advisor. Includes the handoff table per Phase-1 journey and five guardrails.
4. **Proposed architecture.** Three zones, only the third new. Two hooks on the dialer side. Includes the one-turn latency breakdown and the nine-language list.
5. **Where the cost reduction comes from.** Lever 1 as a cheaper minute with the itemised build-up to Rs 2.70 direct cost, Lever 2 as fewer minutes worth buying. States the design constraint we accept.
6. **A twelve-week POC and its scorecard.** Contract and integration, build, live, decide. Six judged metrics and what we need from SBI Card to start.

### 11.2 The product process flows deck

**Status: supporting material.** Maps the current and proposed flows for FlexiPay, Multicarding and CLIP as swimlane diagrams across SBI Card, vendor, AI bot, advisor and customer. Useful for the clarification call and as an annexe to the architecture document.

### 11.3 The internal deck, nine slides

**Status: internal only. Must not go to the client.** Slide 5 names five competitors with capability judgements attached.

1. Title, marked as an internal approach note
2. The business problem, with the funnel and where cost burns
3. What is actually being sold, today versus with AI voice
4. The economics, against the quote and against advisors
5. Who else is in the room, a scored matrix against SBI Card's own seven-point list
6. Where our number comes from, the two levers
7. Bot architecture, high level, three zones and two hooks
8. Bot architecture, low level, the turn loop and failure handling
9. Build roadmap, four workstreams across four weeks with the Day 30 gate

---

## 12. Deliverables to SBI Card

Only two documents ever go to the client. Everything else is internal or is a person on a call.

### Delivered

**The approach note.** Six slides, 8 September 2026.

### Outstanding

**The proposed architecture document.** Shrey named its five sections precisely:

1. Dialer integration approach
2. Bot and NLU stack
3. Language support strategy
4. Handoff and escalation logic
5. Cost-efficiency levers

Written for a mixed audience. Saikat and Sumit read the business sections, and their technology and InfoSec people read the architecture sections, because an InfoSec review is the gate immediately after this.

**What stays out of it.** No competitor names. No competitor comparison. No internal margin arithmetic. No four-week engineering sprint plan, which is our internal build sequence and not theirs. Probably no firm price either, until the clarification call establishes how the agency bills today and where the contacted-minute meter starts.

**Current readiness against the five sections:**

| Section | Status |
|---|---|
| Dialer integration approach | Covered by the three-zone design and two hooks |
| Bot and NLU stack | Covered by the low level design |
| Language support strategy | **Thin.** Needs to be a full section, not a footnote |
| Handoff and escalation logic | Covered by exit paths and warm transfer design |
| Cost-efficiency levers | Covered by the two-lever model |

### Not a document

**The SME clarification call.** A person, prepared, once the requirements note has been read properly. The requirements document arrived on 2 September, so this is the live item and it is what unblocks the architecture document.

### The product itself, in plain terms

Not software SBI Card installs. A service running inside the calling partner's phone system. Four visible parts: something that dials and picks who to call today, something that talks in nine languages, something that hands over to a human advisor when the customer is interested, and a dashboard showing how it went and what it cost.

**One-line version.** A multilingual AI voice agent that runs inside your dialer partner's stack, handles the pitch and qualification on every call, warm-transfers interested customers to your advisors, and reports cost per booked SR against a human baseline.

### Who owns what

| SBI Card | The calling partner | TransOrg |
|---|---|---|
| The script and FAQ glossary | The dialer and SIP trunk | The models and orchestration |
| The calling base and offers | The advisors | The campaign engine |
| The recordings and consent artefacts | The CRM | The dashboards and analytics |
| The customer relationship | | The archive infrastructure |

---

## 13. Open questions, risks and corrections

### 13.1 Corrections needed before anything circulates

**The propensity claim on the competitive matrix is too broad.** We currently mark all four competitors as "No" on propensity scoring of the calling base and make that the whole argument. Skit.ai openly scores propensity to pay on every account and recalibrates segments as signals arrive. It is propensity to pay in collections rather than propensity to convert on cross-sell, which is a genuine distinction, but "nobody in this market sells it" is disprovable in one search. The row must narrow to propensity to convert, modelled on the client's own cross-sell history.

**The latency argument is weaker than written.** We present 900 milliseconds a turn as a strength. Gnani claims under 200 milliseconds because they removed the text layer altogether. We should not be selling speed.

**Savings figures must stay consistent across documents.** The approach note puts the saving at Rs 60 to 75 lakh a month by comparing Rs 6.5 to 7 against Rs 9 at the same volume. An earlier internal draft said Rs 1.03 crore because it also assumed shorter calls, which double-counts. The same-volume method is the correct one. Two decks in circulation with different savings figures would be a problem in a client meeting.

### 13.2 Questions for the clarification call

**On commercials**

1. How does the agency bill SBI Card today: per seat, per contacted minute, or per booking? If it is per booking, the entire comparison reframes.
2. When does the contacted-minute meter start: at connect, at answering-machine-detection clear, or at first bot word?
3. On a warm transfer, who pays for the advisor's minutes?
4. Does the Rs 9 quote include the analytics platform, meaning sentiment, dashboards, speech-to-text audit and the three-year archive? If so, that is a bundle being compared against bare labour.

**On operations**

5. Current average handle time, split into pitch versus post-consent, per product.
6. Current funnel rates: connect percentage, right-party percentage, agreement percentage, consent-to-booking percentage.
7. Is the FlexiPay gate ticket size or call volume? The diagram says input volume under 10K and the scope slide says eligible ATS under Rs 10,000. Those are different rules.
8. What is the retry and re-churn policy in detail beyond the 28-day cycle?

**On scope**

9. The authoritative language list. Shrey's email specifies nine including Gujarati. The charter deck says eight and omits Gujarati. Which governs?
10. Card upgrades, cash products and the insurance vertical are named in the opportunity summary but are outside Phase 1. When do they enter?

**On integration**

11. SIP trunk access and the pacing rules we are permitted to set.
12. CRM API specification for screen-pop and disposition write-back.
13. Sample masked base file and agreed nomenclature.

### 13.3 The risk register

| Risk | Why it matters | What we do about it |
|---|---|---|
| Latency | Every 100 ms across six turns is billed time. If we cannot hold under a second on Indic, the fifty-second target dies. | Week 1 latency harness before any dialog logic is written. |
| Code-mixing | Hinglish and spoken amounts are the top speech-to-text failure. A clean Hindi word error rate proves nothing on its own. | Bake-off on real card audio, scored on code-mixed speech and spoken amounts specifically. |
| Conversion drop | If the bot converts more than about twenty-five percent worse than an advisor, no price gets us to a cheaper booking. | Control arm from day one. Report differences, never levels. |
| Data residency | If InfoSec forces fully on-premise inference, the cost stack and the timeline both move. | Assume India-resident from the start. Budget for self-hosted capacity. |
| Route to market | DialNexa white-labels to agencies. The calling partner could resell them and the bake-off never happens. | Get to the calling partner early, not just to SBI Card. |
| Fixed-cost estimate | The Rs 4.75 floor rests on a Rs 35 lakh monthly fixed base that is our estimate, not a costed plan. | Have finance price the run team before any external quote. |
| Timeline promise | Four weeks to a working product holds for one journey in two languages. It does not hold for three journeys across nine languages with InfoSec clearance. | Make the scope of the Day 30 gate explicit in writing before it is promised to the client. |

---

## 14. Appendix: assumptions register and glossary

### 14.1 Assumptions register

Every number in this document that is ours rather than SBI Card's, in one place, so it can be replaced when their actuals arrive.

| Assumption | Value used | Source | Replace with |
|---|---|---|---|
| Phase-1 volume | 30.7 lakh contacted minutes a month | Derived: Rs 2.76 Cr divided by Rs 9 | Their actual campaign volume |
| Fully loaded advisor seat | Rs 28,000 a month | Industry benchmark for domestic outbound BFSI | Their agency's actual seat cost |
| Advisor talk-time utilisation | Thirty-five percent | Industry benchmark | Their utilisation data |
| Advisor cost per contacted minute | Rs 6.40 | Derived from the two above | Their actuals |
| Human pitch length | Ninety seconds | Estimated from the BLC script structure | Measured from their call recordings in week 1 |
| Bot pitch target | Fifty seconds | Our design target | Measured during the POC |
| Connect rate | Thirty percent | Industry benchmark | Their dialer data |
| Right-party contact | Eighty percent of connects | Industry benchmark | Their dialer data |
| Agreement rate, human | Twelve per 100 conversations | Industry benchmark | Their conversion data |
| Agreement rate, bot | Eleven per 100 conversations | Our estimate, ninety-two percent of human | Measured against control arm |
| Consent to booking | Seventy percent | Industry benchmark | Their data |
| Direct AI cost | Rs 2.70 per contacted minute | Published India-hosted list prices, September 2026 | Re-price at contract |
| Fixed cost base | Rs 35 lakh a month | Our estimate of run team plus amortisation | Finance-costed run plan |
| Bot speaking share | Forty-five percent of a contacted minute | Our estimate | Measured during the POC |

### 14.2 Glossary

| Term | Meaning |
|---|---|
| ACD | Automatic Call Distributor, routes live calls to free agents |
| AHT | Average Handle Time, talk time plus wrap time |
| AMD | Answering Machine Detection |
| ASR | Automatic Speech Recognition, speech to text |
| ATS | Average Ticket Size |
| Barge-in | Customer interrupts and the bot stops speaking |
| BLC | Business, Legal and Compliance, the team that signs off the script |
| C2B link | Click-to-bank link sent to the customer's registered mobile |
| CLIP | Credit Limit Increase Program |
| Containment | Share of calls the bot completes without a human |
| CPA | Cost per acquisition, here cost per booked SR |
| Disposition | The outcome tag applied at the end of a call |
| DNCR | Do Not Call Registry |
| Endpointing | Detecting that the customer has finished speaking |
| FlexiPay | Loan on card, EMI conversion |
| IMAC | SBI Card team handling encryption and file transfer |
| IVR | Interactive Voice Response, here the consent-capture instrument |
| MIS Ops | Management Information Systems Operations, prepares campaign files |
| Multicarding | Issuing an additional card to an existing cardholder |
| NLU | Natural Language Understanding, intent classification |
| PII | Personally Identifiable Information |
| RPC | Right Party Contact |
| SConnect | SBI Card system holding transaction details |
| Screen-pop | Context appearing automatically on the advisor's screen |
| SIP REFER | The protocol message that transfers a live call |
| SR | Service Request, the ticket that books the sale |
| TCCCPR | Telecom Commercial Communications Customer Preference Regulations, 2018 |
| TTS | Text to Speech |
| VAD | Voice Activity Detection |
| WER | Word Error Rate, speech recognition accuracy |
| Whisper summary | Short briefing played to the advisor before connecting the customer |
| Wrap | After-call work, tagging the disposition |

---

*Prepared for internal TransOrg use. Contains competitive assessments drawn from public positioning and unverified. Not for external circulation.*
