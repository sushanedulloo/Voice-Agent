# ADR-003 — The partner owns the call; we are a media endpoint

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 15 September 2026 |
| **Deciders** | TransOrg engineering |

## Context

We do not own the telephony. The calling partner owns the dialer, the SIP trunk, the session
border controller, the recorder, the ACD and the advisors. We need to receive answered call legs,
talk, and hand interested customers back.

The tempting design is for the bot to control the call: answer, qualify, then issue a SIP REFER to
transfer the customer to an advisor. It does not survive contact with a real contact centre.

## Decision

**The partner's dialer remains the B2BUA and master of the call for its entire duration. We are a
media endpoint they dial into, and we hand control back to them for the transfer.**

Concretely:
- They send `INVITE sip:<campaign>@our-sbc` for each answered leg. We are a UAS, not a UAC.
- We answer with a single-codec SDP answer: **PCMA/8000** (A-law — India), ptime 20,
  RFC 4733 out-of-band DTMF.
- To transfer we either REFER to a **queue DID**, or call a REST endpoint on their dialer and let
  them re-bridge their own leg. We never target a named advisor.
- We never originate a call. We never dial, retry, or call back.

## Rationale

**SIP REFER does not reliably survive a B2BUA.** Their SBC terminates our dialog, so a `Replaces`
tuple we compute refers to a dialog the far side never saw. Oracle and Ribbon SBCs variously proxy,
reject, or silently convert REFER into a fresh INVITE. Designing a transfer we control means
designing against every SBC vendor's quirks with no ability to test them.

**We do not know advisor availability.** That state lives in their ACD. Referring to a specific
advisor SIP URI is wrong in principle, not just in practice.

**Recording continuity.** If we leave the call and it re-anchors elsewhere, their recorder starts a
new session — two files, two identifiers, a broken audit trail. CR-103 requires an unbroken trail.
Keeping media anchored on their SBC keeps it one continuous recording.

**Regulatory perimeter.** Originating calls would make us the sender under TCCCPR: DLT
registration, 140-series CLI, DNCR scrubbing, abandoned-call ratios, and penalties up to
₹10 lakh per violation plus service suspension. That perimeter belongs to the Principal Entity.
**Do not take it.**

## Consequences

**Benefits.**
- No SBC-compatibility matrix to maintain.
- Single continuous recording, single call identity, audit trail intact.
- Regulatory exposure stays with the party that already holds the DLT registration.
- Simplest possible failure mode: if we die, the dialer routes to humans (NFR-203).

**Costs.**
- We depend on the partner to build or expose a transfer endpoint. This is an integration
  dependency on a third party we do not contract with directly, on a critical path.
- We cannot guarantee transfer success ourselves — we can only report what we asked for.
- Whisper audio costs the customer 3–6 seconds of dead air unless the partner plays hold audio.

**Correlation strategy.** Adopt *their* call identifier as our primary key rather than minting our
own. SIP `Call-ID` changes at every B2BUA hop, so it cannot be the join key. An audit trail across
systems we do not own is built by borrowing their key and emitting it on every log line and every
CRM write. Mint `bot_session_id` as secondary. Request RFC 7989 `Session-ID` support if their SBC
has it; assume it does not.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| SIPREC / media forking | One-directional media to a recorder. No standard path to inject audio back — fine for agent-assist, useless for a talking bot. |
| Bot as originator | Takes on the partner's entire regulatory perimeter. Non-starter. |
| CPaaS media streaming (Twilio ConversationRelay, Exotel AgentStream, Plivo) | Inserts a second telco into the path, collides with DLT numbering, and in Twilio's case takes STT/TTS choice partly out of our hands. Keep as a fallback if the partner cannot route SIP to us. |
| Attended REFER with `Replaces` | The correct protocol answer; unreliable through a B2BUA we do not control. Use only if their SBC is proven to honour it. |

## Interface control document — what to get in writing

Before any code is written, these must be agreed and frozen:

1. Direction of setup (they INVITE us), SIP URI, IP allowlist, TLS/SRTP, CPS and concurrency caps
2. **Codec: PCMA/8000 only, ptime 20, RFC 4733 DTMF** — asserted in code, not trusted to defaults
3. Exact `X-` header / `User-to-User` token list, and confirmation their SBC will not strip it
4. Transfer contract: queue DID or REST endpoint, and whether REFER-with-Replaces is honoured
5. AMD ownership — **they run it**; we receive `AnsweredBy`, or they bridge only humans
6. Their call identifier present in the INVITE, and a CDR feed back to us
7. Media hosted in Mumbai; the RTP path must not leave India
8. Written answers on the compliance questions in R-14 and R-15

> Note on `User-to-User` (RFC 7433): practical ceiling is ~128 bytes. Use it for an **opaque token
> only**, never a payload. Full context goes to the CRM keyed by that token, written at
> qualification time rather than at transfer time so the screen-pop does not race it.

## References

- RFC 5589 (SIP call transfer), RFC 7433 (UUI), RFC 7865/7866 (SIPREC), RFC 7989 (Session-ID)
- TCCCPR 2018 Reg 2(a), 2(e), 4, 12(2); Schedules I and II
