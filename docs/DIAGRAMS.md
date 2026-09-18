# Architecture & Design Diagrams
## SBI Card AI-BOT Outbound Voice Agent

| | |
|---|---|
| **Document** | DIAG-VOICE-001 |
| **Version** | 0.1 |
| **Date** | 15 September 2026 |

All diagrams are Mermaid source, versioned with the code. No binary images — they rot, they cannot
be diffed, and nobody can tell which one is current.

**Contents**
1. [System context (C4 L1)](#1-system-context--c4-level-1)
2. [Container view (C4 L2)](#2-container-view--c4-level-2)
3. [Component view (C4 L3)](#3-component-view--voice-agent-internals)
4. [Sequence — one conversational turn](#4-sequence--one-conversational-turn)
5. [Sequence — FlexiPay happy path](#5-sequence--flexipay-happy-path)
6. [Sequence — disqualification](#6-sequence--disqualification-the-common-case)
7. [Sequence — warm transfer](#7-sequence--warm-transfer-with-whisper-and-screen-pop)
8. [Sequence — safe exit](#8-sequence--safe-exit)
9. [Dialog state machine](#9-dialog-state-machine)
10. [Entity-relationship model](#10-entity-relationship-model)
11. [Campaign data pipeline](#11-campaign-data-pipeline)
12. [Deployment view](#12-deployment-view)
13. [Per-product flow variance](#13-per-product-flow-variance)

---

## 1. System context — C4 Level 1

Who talks to what. Only the blue box is ours.

```mermaid
flowchart TB
    CUST(["Cardholder<br/><i>pre-approved, called cold</i>"])
    ADV(["Advisor<br/><i>employed by calling partner</i>"])
    OPS(["SBI Card MIS<br/>&amp; Compliance"])

    subgraph SBIC["SBI Card"]
        BASE["Calling base<br/>zone-segmented, GPG"]
        SCONN["SConnect<br/>offer variables"]
        SRSYS["SR booking systems"]
        BLC["BLC script +<br/>FAQ glossary"]
    end

    subgraph PART["Calling Partner"]
        DIAL["Predictive /<br/>Progressive Dialer"]
        CRM["Partner CRM"]
        POOL["Advisor idle pool"]
    end

    SYS["<b>TransOrg Voice Agent</b><br/>pitch · probe · qualify · hand off"]

    BASE --> DIAL
    SCONN -.-> BASE
    BLC -.approved content.-> SYS
    DIAL -->|answered SIP leg| SYS
    SYS <-->|RTP audio| CUST
    SYS -->|SIP REFER + whisper| POOL
    POOL --> ADV
    ADV <--> CUST
    ADV --> SRSYS
    SYS -->|disposition, consent,<br/>recording pointer| CRM
    SYS -->|dashboards, daily MIS,<br/>audit extract| OPS

    style SYS fill:#d7ebff,stroke:#0b5fa5,stroke-width:3px
```

---

## 2. Container view — C4 Level 2

What runs inside our boundary.

```mermaid
flowchart TB
    DIAL[/"Partner Dialer<br/>SIP + RTP"/]
    CRMAPI[/"Partner CRM API<br/>mTLS"/]

    subgraph EDGE["Media edge"]
        GW["<b>Media Gateway</b><br/>SIP UA, RTP, jitter buffer<br/>codec handling, recording tap"]
    end

    subgraph BRAIN["Conversation plane"]
        ORCH["<b>Orchestrator</b><br/>state machine, turn control<br/>barge-in, timers"]
        ASR["<b>ASR</b><br/>streaming Indic, 8 kHz"]
        NLU["<b>Intent Router</b><br/>closed-set classification"]
        TTS["<b>TTS + Audio Cache</b><br/>pre-rendered lines,<br/>runtime synthesis for variables"]
    end

    subgraph CONTENT["Content plane"]
        SCRIPT[("Script Store<br/>versioned nodes")]
        GLOS[("FAQ Glossary<br/>versioned")]
    end

    subgraph DATA["Data plane"]
        EVT["Event Log<br/>append-only"]
        DB[("Call Store<br/>turns, dispositions,<br/>consent events")]
        ARC[("Archive<br/>audio + text, 3 yr,<br/>encrypted, India")]
    end

    subgraph ANALYTICS["Analytics plane"]
        DASH["Dashboards<br/>funnel, cost/SR"]
        ML["Models<br/>propensity · best-time-to-call<br/>sentiment · STT audit"]
    end

    DIAL <--> GW
    GW <--> ORCH
    ORCH <--> ASR
    ORCH <--> NLU
    ORCH <--> TTS
    NLU -.reads.-> GLOS
    ORCH -.reads.-> SCRIPT
    TTS -.reads.-> SCRIPT
    ORCH --> EVT
    EVT --> DB
    GW --> ARC
    DB --> ARC
    DB --> ML
    ML --> DASH
    DB --> DASH
    ORCH -->|disposition,<br/>consent| CRMAPI
    ORCH -->|SIP REFER| DIAL

    style BRAIN fill:#e8f4ff,stroke:#0b5fa5
    style CONTENT fill:#fff4e0,stroke:#b8860b
```

**Why the content plane is separate.** BLC-approved script and glossary content changes on a
compliance cadence, not an engineering one. NFR-401 requires a script change to deploy without a
code release. Anything else means a legal edit waits on a sprint.

---

## 3. Component view — Voice Agent internals

The turn loop, in detail.

```mermaid
flowchart LR
    subgraph IN["Inbound audio"]
        RTP["RTP<br/>8 kHz"] --> VAD["VAD +<br/>End-of-turn<br/>detector"]
        VAD --> ASRS["Streaming ASR<br/><i>partials during speech</i>"]
    end

    subgraph DECIDE["Decision"]
        ASRS --> NORM["Numeric &amp;<br/>lexicon normaliser<br/><i>lakh, hazaar, mixed</i>"]
        NORM --> ROUTE{"Intent Router"}
        ROUTE -->|in glossary| FAQSEL["Select approved<br/>FAQ answer"]
        ROUTE -->|script intent| NEXT["Next script node"]
        ROUTE -->|out of scope| FB["Node fallback"]
        ROUTE -->|stop / abuse| EXIT["Safe exit"]
    end

    subgraph OUT["Outbound audio"]
        FAQSEL --> SEL
        NEXT --> SEL
        FB --> SEL
        SEL{"Utterance<br/>resolver"} -->|fixed line| CACHE["Audio cache<br/><i>pre-rendered</i>"]
        SEL -->|has variables| SYNTH["Runtime TTS<br/><i>amounts, names</i>"]
        CACHE --> MIX["Playout +<br/>barge-in cancel"]
        SYNTH --> MIX
        MIX --> RTPO["RTP out"]
    end

    EXIT --> MIX
    style DECIDE fill:#e8f4ff
```

> **The single most important property of this diagram:** the LLM sits in `Intent Router` — it
> *chooses*. It is absent from the output path entirely. Every utterance resolves to approved
> content. That is what makes FR-203 verifiable from logs alone.

---

## 4. Sequence — one conversational turn

The latency-critical path. Budget in `docs/DESIGN.md`.

```mermaid
sequenceDiagram
    autonumber
    participant C as Customer
    participant GW as Media Gateway
    participant O as Orchestrator
    participant A as Streaming ASR
    participant R as Intent Router
    participant T as TTS / Cache

    C->>GW: speech (RTP, 8 kHz)
    GW->>A: audio frames (streaming)
    A-->>O: partial transcripts
    Note over GW,O: ASR runs *during* speech.<br/>Only the tail costs latency.
    C->>GW: silence
    GW->>O: end-of-turn detected
    O->>A: finalise
    A-->>O: final transcript
    O->>R: transcript + current node + allowed intents
    R-->>O: intent + confidence + target node
    alt utterance is a fixed approved line
        O->>T: fetch cached audio (node, language)
        T-->>O: audio (cache hit)
    else utterance contains campaign variables
        O->>T: synthesise variable span only
        T-->>O: audio (streamed, first byte fast)
    end
    O->>GW: play
    GW->>C: bot audio
    O->>O: append turn to event log
    Note over C,T: Target ≤ 1000 ms P95,<br/>end of speech → first bot audio.
```

---

## 5. Sequence — FlexiPay happy path

Per `CH-S9`. The advisor runs the IVR; the bot never touches it.

```mermaid
sequenceDiagram
    autonumber
    participant D as Partner Dialer
    participant B as Voice Agent
    participant C as Customer
    participant A as Advisor
    participant CRM as Partner CRM
    participant S as SBI Card

    D->>D: gate — FlexiPay eligible segment
    D->>B: SIP INVITE (answered leg + masked ref)
    B->>C: greeting, approved script, language from zone
    C-->>B: response
    B->>C: pitch with offer variables from campaign record
    C-->>B: question
    B->>B: route to approved FAQ entry
    B->>C: approved answer
    C-->>B: agreement
    B->>B: record verbal consent event (timestamped)
    B->>CRM: disposition = interested, consent event, recording ptr
    B->>D: SIP REFER → advisor idle pool
    B-->>A: whisper summary + screen-pop context
    A->>C: identity verification (PIN code, year of birth)
    A->>C: secured IVR — press 1 to accept
    C-->>A: keypress captured
    A->>S: submit SR
    S-->>A: SR auto-created
    Note over B,A: Bot owns ~50 s.<br/>Everything after transfer is unchanged<br/>from today's process.
```

---

## 6. Sequence — disqualification, the common case

~88% of contacts. This path is where all the savings are, so it is the one to optimise.

```mermaid
sequenceDiagram
    autonumber
    participant D as Partner Dialer
    participant B as Voice Agent
    participant C as Customer
    participant CRM as Partner CRM

    D->>B: SIP INVITE (answered leg)
    B->>C: greeting + pitch
    C-->>B: "nahi bhai, abhi nahi chahiye"
    B->>B: intent = NOT_INTERESTED (confidence high)
    B->>C: approved objection-handling line (attempt 1)
    C-->>B: declines again
    B->>B: second decline → stop probing
    B->>C: approved closing line
    B->>CRM: disposition = not interested + reason code
    B->>D: release leg
    Note over B,CRM: No advisor time consumed at all.<br/>Optimisation target is<br/>*time to disqualify*, not time to sell.
```

---

## 7. Sequence — warm transfer with whisper and screen-pop

Get this wrong and the advisor re-asks everything, destroying the time the bot saved (R-13).

```mermaid
sequenceDiagram
    autonumber
    participant B as Voice Agent
    participant D as Dialer / ACD
    participant A as Advisor
    participant C as Customer
    participant CRM as Partner CRM

    B->>CRM: write context (masked ref, product,<br/>intent trail, consent event)
    B->>C: "connecting you to my colleague"
    B->>D: SIP REFER + correlation id
    D->>D: select free advisor from idle pool
    D->>A: ring
    A->>D: answer
    D->>A: whisper summary (customer not yet bridged)
    CRM-->>A: screen-pop on correlation id
    Note over A: Advisor knows product, interest,<br/>and what was already asked
    D->>D: bridge advisor ↔ customer
    A->>C: takes over
    Note over B,CRM: Recording continuity and a single<br/>correlation id across both legs — IR-109.
```

---

## 8. Sequence — safe exit

Non-negotiable. Any turn, any state.

```mermaid
sequenceDiagram
    autonumber
    participant C as Customer
    participant B as Voice Agent
    participant CRM as Partner CRM

    C-->>B: "do not call me again" / abuse / repeated silence
    B->>B: safe-exit interceptor fires<br/>(evaluated before script routing)
    B->>C: approved closing line
    B->>CRM: disposition + DNC flag + reason
    B->>B: mark record — suppress from future campaigns
    B->>B: emit compliance event to audit log
    Note over B,CRM: Interceptor runs on *every* turn,<br/>ahead of normal routing.<br/>It cannot be reached only via<br/>a script path — CR-107.
```

---

## 9. Dialog state machine

FR-201. The script is a state machine; the model chooses transitions, never content.

```mermaid
stateDiagram-v2
    [*] --> Connecting
    Connecting --> AMDCheck: leg answered
    AMDCheck --> Dispose: machine detected
    AMDCheck --> Greeting: human detected

    Greeting --> LanguageAdapt: response received
    Greeting --> Reprompt1: silence
    LanguageAdapt --> Pitch: language settled

    Pitch --> Probe: pitch delivered
    Probe --> FAQAnswer: in-glossary question
    FAQAnswer --> Probe
    Probe --> ObjectionHandle: objection
    ObjectionHandle --> Probe: attempt < 2
    ObjectionHandle --> Closing: attempt = 2
    Probe --> Fallback: out-of-scope question
    Fallback --> Probe
    Probe --> InterestCheck: signal detected

    InterestCheck --> Agreed: yes
    InterestCheck --> Closing: no
    Agreed --> ConsentCapture
    ConsentCapture --> Transfer
    Transfer --> [*]

    Closing --> Dispose
    Dispose --> [*]

    Reprompt1 --> Reprompt2: silence again
    Reprompt1 --> Pitch: response
    Reprompt2 --> Dispose: silence again
    Reprompt2 --> Pitch: response

    state SafeExit
    SafeExit --> Dispose
    note right of SafeExit
        Reachable from EVERY state.
        DNC request, abuse, stop request.
        Evaluated before normal routing.
    end note
```

**Every node carries:** approved utterance (per language) · permitted intents and their targets ·
prohibited content · fallback utterance · timeout and re-prompt. Nothing else is permitted at a node.

---

## 10. Entity-relationship model

DR-101 to DR-106. Note what is absent: there is no customer entity, no name, no card number.
`masked_ref_id` is the only customer key we ever hold (CR-101).

```mermaid
erDiagram
    CAMPAIGN ||--o{ CAMPAIGN_RECORD : contains
    CAMPAIGN_RECORD ||--o{ ATTEMPT : "dialled in"
    CAMPAIGN_RECORD ||--o{ CALL : "produces"
    CALL ||--|{ TURN : "consists of"
    CALL ||--o| CONSENT_EVENT : "may capture"
    CALL ||--|| DISPOSITION : "ends with"
    CALL ||--o| TRANSFER : "may hand off"
    CALL ||--|| RECORDING : "produces"
    CALL ||--|| TRANSCRIPT : "produces"
    TURN }o--|| UTTERANCE : "played"
    UTTERANCE }o--|| SCRIPT_VERSION : "belongs to"
    SCRIPT_NODE }o--|| SCRIPT_VERSION : "belongs to"
    SCRIPT_NODE ||--|| UTTERANCE : "speaks"
    FAQ_ENTRY }o--|| GLOSSARY_VERSION : "belongs to"
    FAQ_ENTRY ||--|| UTTERANCE : "answers with"
    TURN }o--o| FAQ_ENTRY : "matched"

    CAMPAIGN {
        uuid campaign_id PK
        string product_code "FLEXIPAY|MULTICARD|CLIP"
        string script_version FK
        string glossary_version FK
        date   campaign_date
        string status
    }
    CAMPAIGN_RECORD {
        uuid   record_id PK
        uuid   campaign_id FK
        string masked_ref_id "ONLY customer key — no PII"
        string zone
        string language_hint
        json   offer_variables "amount, tenure — from SConnect"
        int    attempt_count
        date   rechurn_due
    }
    ATTEMPT {
        uuid   attempt_id PK
        uuid   record_id FK
        ts     attempted_at
        string result "connected|no_answer|busy|invalid"
    }
    CALL {
        uuid   call_id PK
        uuid   record_id FK
        string correlation_id "spans dialer, bot, CRM — IR-109"
        string dialer_leg_id
        ts     started_at
        ts     ended_at
        int    talk_seconds
        string language_used
        bool   language_switched
        string script_version
        string glossary_version
    }
    TURN {
        uuid   turn_id PK
        uuid   call_id FK
        int    seq
        string state_node
        string customer_transcript
        string detected_intent
        float  confidence
        uuid   utterance_id FK
        int    latency_eot_ms
        int    latency_asr_ms
        int    latency_route_ms
        int    latency_tts_ms
        bool   barge_in
    }
    UTTERANCE {
        uuid   utterance_id PK
        string script_version FK
        string language
        string kind "script|faq|fallback|reprompt"
        string text "APPROVED content only"
        string audio_uri "pre-rendered, nullable"
        bool   has_variables
    }
    SCRIPT_NODE {
        string node_id PK
        string script_version FK
        string product_code
        uuid   utterance_id FK
        json   allowed_intents
        uuid   fallback_utterance_id FK
        int    timeout_ms
    }
    FAQ_ENTRY {
        uuid   faq_id PK
        string glossary_version FK
        string product_code
        string canonical_question
        uuid   utterance_id FK
    }
    CONSENT_EVENT {
        uuid   consent_id PK
        uuid   call_id FK
        string consent_type "verbal_agreement|ivr_keypress"
        ts     captured_at
        string recording_uri
        string content_hash "tamper evidence"
    }
    DISPOSITION {
        uuid   disposition_id PK
        uuid   call_id FK
        string code
        string reason
        bool   dnc_flag
        ts     written_to_crm_at
    }
    TRANSFER {
        uuid   transfer_id PK
        uuid   call_id FK
        string advisor_pool
        string whisper_text
        ts     refer_sent_at
        ts     accepted_at
        bool   screen_pop_confirmed
    }
    RECORDING {
        uuid   recording_id PK
        uuid   call_id FK
        string uri
        string codec
        int    duration_s
        date   retention_until "3 years — FR-702"
    }
    TRANSCRIPT {
        uuid   transcript_id PK
        uuid   call_id FK
        string uri
        date   retention_until
    }
```

**Design notes.**
- `script_version` and `glossary_version` are stamped on `CALL`, not looked up live. A call must be
  reconstructable years later against the exact content that was approved at the time (FR-204).
- `TURN` stores per-stage latency so NFR-101 is measurable from data, not from a load test.
- `CONSENT_EVENT.consent_type` is deliberately an enum with both values — it absorbs whichever way
  open item OI-1 resolves without a schema migration.
- `content_hash` makes consent artefacts tamper-evident (CR-102).

---

## 11. Campaign data pipeline

Steps 1–8 are SBI Card's existing, unchanged process. We join at step 9.

```mermaid
flowchart LR
    A["1 · Analytics/IT<br/>prepare base<br/><i>zone-segmented</i>"] --> B["2 · IMAC<br/>GPG encrypt<br/>WinSCP"]
    B --> C["3 · Vendor<br/>auto-decrypt<br/>per nomenclature"]
    C --> D["4 · Touchless<br/>dialer upload"]
    D --> E["5 · DNCR<br/>scrubbing"]
    E --> F["6 · MIS Ops<br/>receives<br/><i>PII stripped</i>"]
    F --> G["7 · Campaign<br/>file prep"]
    G --> H["8 · Dial<br/>predictive /<br/>progressive"]
    H --> I["<b>9 · BOT</b><br/>pitch · probe ·<br/>qualify"]
    I --> J["10 · Advisor<br/>verify · consent ·<br/>SR"]

    style A fill:#eee
    style B fill:#eee
    style C fill:#eee
    style D fill:#eee
    style E fill:#eee
    style F fill:#eee
    style G fill:#eee
    style H fill:#eee
    style I fill:#d7ebff,stroke:#0b5fa5,stroke-width:3px
    style J fill:#ffe9d6
```

---

## 12. Deployment view

India region only (CR-105). Autoscaled to the calling window, not 24×7 (NFR-204).

```mermaid
flowchart TB
    subgraph PARTNER["Calling Partner DC"]
        SBC["SBC / SIP trunk"]
        DIALER["Dialer + ACD"]
        CRMS["CRM"]
    end

    subgraph INDIA["India Region — private cloud or partner DC"]
        subgraph AZ1["Availability Zone 1"]
            MG1["Media Gateway<br/>CPU · stateful sessions"]
            OR1["Orchestrator<br/>CPU · stateless"]
        end
        subgraph AZ2["Availability Zone 2"]
            MG2["Media Gateway"]
            OR2["Orchestrator"]
        end
        subgraph GPUP["Inference pool — autoscaled to calling window"]
            ASRP["ASR workers<br/>GPU · ~50 streams each"]
            LLMP["Router model<br/>GPU · ~80 streams each"]
            TTSP["TTS workers<br/>GPU · low duty<br/><i>most audio is cached</i>"]
        end
        subgraph STATE["State"]
            PG[("Call Store<br/>Postgres")]
            OBJ[("Object store<br/>audio + text, 3 yr")]
            KV["Audio cache<br/>pre-rendered lines"]
            VAULT["Key vault"]
        end
        OBS["Observability<br/>metrics · traces · audit log"]
    end

    SBC <-->|SIP/RTP| MG1
    SBC <-->|SIP/RTP| MG2
    DIALER -.control.-> SBC
    MG1 --> OR1
    MG2 --> OR2
    OR1 --> ASRP
    OR1 --> LLMP
    OR1 --> TTSP
    OR1 --> KV
    OR1 --> PG
    MG1 --> OBJ
    OR1 -->|mTLS| CRMS
    OR1 --> OBS
    PG --> OBS
    VAULT -.-> OR1
    VAULT -.-> MG1

    style INDIA fill:#f4f9ff,stroke:#0b5fa5
    style GPUP fill:#fff4e0
```

**Scaling notes.** Media gateways are stateful and scale with concurrent legs (~250 peak, headroom
to 500 — NFR-201). Orchestrators are stateless and scale horizontally. GPU pools scale on queue
depth and idle outside the calling window — this is worth roughly 3× on inference cost versus
running continuously. See `cost_model.py`.

---

## 13. Per-product flow variance

The bot's job is near-identical across products. What differs is everything after the yes.

```mermaid
flowchart TD
    START(["Bot: pitch, probe,<br/>detect agreement"]) --> Q{"Customer<br/>agrees?"}
    Q -->|No| DISP["Bot disposes<br/>not interested"]
    Q -->|Yes| P{"Product?"}

    P -->|FlexiPay| F1["Transfer to advisor"]
    F1 --> F2["Advisor verifies identity"]
    F2 --> F3["<b>Advisor</b> runs secured IVR<br/>press 1 to accept"]
    F3 --> F4["Advisor submits SR"]

    P -->|Multicarding| M1["Transfer to advisor"]
    M1 --> M2["Advisor verifies identity"]
    M2 --> M3["Advisor fills form,<br/>triggers C2B link"]
    M3 --> M4["Customer: OTP +<br/>prefilled form"]
    M4 --> M5["<b>No IVR at all</b>"]

    P -->|CLIP| C1{"OI-1<br/>unresolved"}
    C1 -->|"Charter map + RACI"| C2["<b>Bot</b> runs secured IVR,<br/>then transfers"]
    C1 -->|"CLIP flowchart"| C3["Transfer, then<br/><b>advisor</b> runs IVR"]
    C2 --> C4["Advisor submits SR"]
    C3 --> C4

    style C1 fill:#ffd7d7,stroke:#c00,stroke-width:2px
    style DISP fill:#eee
```

> The red node is [OI-1](SRS.md#10-open-items). It changes CLIP call duration, our position in the
> regulated consent chain, and per-product pricing. Do not design past it — design *around* it, via
> `CONSENT_EVENT.consent_type`.

---

## Rendering

GitHub, GitLab and most Markdown viewers render Mermaid natively. For a local check:

```bash
npx -y @mermaid-js/mermaid-cli -i docs/DIAGRAMS.md -o /tmp/diagrams.md
```
