# IDEA_SCOPE.md

**Project codename:** `AWAAZ-PAY`
**Event:** Sarvam Epoch Buildathon by GrowthX · Sun 26 July 2026 · Razorpay Arena, Bengaluru
**Build window:** 10:30 AM – 4:30 PM IST (6 hours) · Demo 5:30–6:30 PM
**Status:** Idea locked. Scope approved. Implementation not started.

---

## 0. How to use this document

This is the control plane for the build. Read it before proposing or making any change.

**Rules of engagement for the AI coding assistant:**

1. Identify the active milestone and its acceptance test before writing code.
2. Do not pull Parking Lot items (§16) into the critical path unless the builder explicitly rescopes.
3. When blocked, simplify or route around. Do not silently redesign the product.
4. At every milestone boundary, report: does the golden path still work / what rubric evidence improved / what is now the largest demo risk / what should be cut.
5. Protect the final hardening window (M6). It is not negotiable.

**Event-rules compliance note.** This document is a *scope*, produced before the event using the Idea + Scope Copilot prompt that the organizers publish in the Builder Handbook (§04) and explicitly endorse. It deliberately contains **no implementation code** — only interface contracts, schemas, state definitions, and acceptance tests. All code is to be written on the floor after 10:30 AM. Standard scaffolding (FastAPI, SDK installs, accounts) and AI coding assistants are permitted starting points per the handbook Rules section. If any part of the origin is borderline, flag it in the submission notes — the handbook rewards flagging and treats concealment as auto-disqualification.

---

## 1. Source provenance

Statements in this document are tagged so nothing gets treated as more certain than it is.

| Tag | Meaning |
|---|---|
| **[V]** | Verified from Sarvam docs or the GrowthX Builder Handbook |
| **[B]** | Stated by the builder |
| **[I]** | Inference — must be confirmed before it becomes load-bearing |
| **[?]** | Unknown. Has a named spike and a named fallback. |

**Unresolved at time of writing — resolve these first:**

- **[?]** Does Saaras v3 streaming expose a per-utterance or per-token confidence signal? *This is the single most load-bearing unknown in the build.* Spike in M0. Fallback defined in §8.4.
- **[?]** What exactly is **Sarvam Conversations** (handbook: "real-time voice: call and speak, at much lower latency")? If it is a managed realtime voice API it may replace most of the audio layer. Spike in M0, timeboxed to 15 minutes.
- **[?]** Does Bulbul v3 support Odia? Bulbul v3 is documented at 11 languages while Saaras v3 covers 23. **[V]** This is why the locked demo language is Hindi + Hinglish, not Odia (§3).
- **[?]** The rubric L1–L5 ladder tables did not render when the handbook was fetched remotely. Read the actual ladders on the floor and reconcile against §4 before committing to the target vector.

---

## 2. The problem, in one paragraph

A migrant construction worker in Kochi sends money home to Odisha every month. He has a feature phone and no data plan. The number-based payment flows on his phone speak to him in English through a screen he cannot read comfortably, so he hands cash to an agent at the site gate and accepts a 2–5% cut for solving the reading problem. **[V from Idea Library]** The job is not "transcribe speech." The job is "move money to the right person, in the right amount, with no screen, over a bad line, and never once move it wrong."

---

## 3. Idea Lock

| Decision | Locked answer |
|---|---|
| **One-sentence product** | A phone number you call to send money home in your own language, where a mis-hear can never become a wrong transfer, and where the system stops making the same mistake to you twice. |
| **User** | Feature-phone remittance sender, Hindi/Hinglish speaking, calling from a noisy worksite |
| **Job completed** | Money moved to the correct payee in the correct amount, confirmed, with a receipt — or explicitly not moved and the caller told so |
| **Hard input** | Narrowband telephony audio (8 kHz, codec in path), site noise, code-switched amounts, Indian proper nouns |
| **Final output / state change** | A committed transfer against the mocked rail with a `txn_id`, plus an SMS receipt. Or a clean `ABORTED` state with nothing moved. |
| **Sarvam parameter (scored)** | **Voice Experience** — declared explicitly at demo time |
| **Additional capability** | None. No Doc AI. No Dubbing. Additional Sarvam capabilities add no points **[V]** and cost hours. |
| **Exact Sarvam APIs** | Saaras v3 (streaming STT), Bulbul v3 (streaming TTS), Sarvam-30B (slot extraction). Sarvam-105B **not** in the hot path. |
| **Locked language subset** | Hindi + Hinglish only. Latin-digit code-switching required ("paanch hazaar", "5 thousand", "5k" all valid). |
| **Team advantage** | **[B]** Deep production reps on Indian-language voice bots over telephony: amount pronunciation, Hinglish code-switch handling, barge-in and endpointing failure modes, confidence-triage on garbled ASR |
| **Creativity thesis** | Accuracy on a bad line is not a model property, it is a *learned per-caller* property. The system builds a private lexicon of how *you* say your payees and amounts, and consults it before it doubts you. |
| **Delight thesis** | The second call is visibly faster than the first, because it remembered your correction. Delight is competence that compounds. |
| **Memory boundary** | Declared framing: **cross-session correction retention keyed to caller identity.** Persisted, governed, and it demonstrably changes gate behaviour. Nothing else claims Memory. |
| **Demo proof** | A judge calls, corrects a mis-heard payee, hangs up, calls back, and the same payee resolves first-try with no gate |
| **Non-goals** | §15 |

---

## 4. Rubric target vector

Scoring architecture **[V]**: one level = one point; weighted = level × multiplier; max 50.

| Parameter | Mult | Card as written | Target | The one proof that moves it |
|---|---:|---|---|---|
| Job-to-be-done completion | 2.5× | L4 (10) | **L4 (10)** | Three consecutive clean commits, no builder intervention. **Do not chase L5** — 90%+ over noisy telephony is not achievable in six hours and chasing it burns the ledger. |
| Memory and Context | 1× | L2 (2) | **L4–L5 (4–5)** | A correction made in call 1 changes gate behaviour in call 2 |
| Creativity | 1.5× | L3 (4.5) | **L4–L5 (6–7.5)** | The ledger reframes the accuracy problem, structurally, not cosmetically |
| Impact | 1.5× | L4 (6) | **L4–L5 (6–7.5)** | Baseline (2–5% agent cut) named in the first 30 seconds with a real measured number behind it |
| Delight | 1× | L2 (2) | **L4 (4)** | The second-call moment, plus abort landing cleanly mid-readback |
| **Voice Experience** | 2.5× | L4 (10) | **L5 (12.5)** | Noisy room, code-switched amount, mid-readback barge-in abort, all live and unrehearsed |
| | | **≈34.5 / 50** | **≈42–45 / 50** | |

**Evidence assignment — no double counting.** **[V: rubric forbids it]**

- Handling bad audio in the moment → **Voice Experience only.** Not Delight.
- Persisting a correction across calls → **Memory only.** Not Creativity.
- Reframing accuracy as learned-per-caller → **Creativity only.** Not Memory.
- The felt experience of the faster second call → **Delight only.**
- Money actually arriving correctly → **JTBD only.**

**The strategic point:** improving the ASR moves Voice L4→L5 for +2.5. Fixing Memory + Creativity + Delight is worth +7 to +8.5 for less engineering. Every other team that picks this Idea Library card will optimise the confirmation loop, because the card tells them to. **The ledger is the entire differentiator. Protect it above everything except a working phone call.**

---

## 5. Architecture

```
  Caller's phone
        │  PSTN
        ▼
  Twilio Voice ──── <Stream> bidirectional ────┐
        │  (8 kHz mulaw)                       │
        ▼                                      ▼
  FastAPI service  ◄──── WebSocket ────►  Audio bridge
        │
        ├──► Saaras v3 streaming STT ──► hypothesis + confidence[?]
        │
        ├──► CORRECTION LEDGER (SQLite) ──► per-caller lexicon rescoring
        │
        ├──► Sarvam-30B ──► slot extraction ONLY (never decides)
        │
        ├──► COMMIT STATE MACHINE (plain Python, deterministic)
        │         └──► mocked rail: resolve / transfer / status
        │
        └──► Bulbul v3 streaming TTS ──► readback audio
```

### 5.1 The governing architectural rule

> **The LLM is a slot filler. It is never a decision maker. No LLM output can trigger a commit.**

Sarvam-30B extracts `{payee_phrase, amount_phrase, intent}` from a transcript and returns structured JSON. A deterministic Python state machine decides whether to advance, re-ask, or commit. A judge who knows what they are looking at will probe exactly this. If the answer is "the model decides when to send money," the Voice Experience and JTBD scores both collapse.

### 5.2 Telephony decision

**Primary: Twilio Voice + Media Streams**, following Sarvam's official Twilio voice-agent integration guide. **[V: guide exists]** Fewest moving parts, one number pointed at one webhook.

**Fallback if Twilio Indian DID provisioning stalls:** any number that rings from an Indian mobile. A Twilio US number is ugly and costs more per minute but is a valid demo path. **This must be verified working before the event begins** — it is the named kill condition (§17).

**Do not** wire LiveKit SIP, Exotel, or Pipecat unless the Twilio path is dead by 11:00. Switching audio stacks after 11:00 ends the build.

---

## 6. Verified Sarvam API surface and constraints

All **[V]** from Sarvam docs unless noted.

| Capability | Model / API | Constraints that will bite |
|---|---|---|
| STT (live) | **Saaras v3**, streaming | 23 languages. Modes: `transcribe`, `translate`, `verbatim`, `translit`, `codemix`. **Use `codemix`** — it returns Hindi in Devanagari with English words preserved in Latin, which is what a Hinglish amount actually looks like. Telephony-tuned. |
| STT (batch/corpus) | **Saaras v3**, batch | For scoring the recorded corpus offline. REST endpoint caps at 30s clips; use batch for anything longer. |
| TTS | **Bulbul v3**, WebSocket streaming | 30+ voices, 11 languages. `output_audio_codec` supports **mulaw** — match Twilio. Pronunciation dictionary via `dict_id`. `enable_preprocessing` exists but **do not rely on it for numerals** (§10). |
| LLM | **Sarvam-30B** | 32k context. Speed tier. Slot extraction only. |
| LLM | Sarvam-105B | 128k, reasoning tier. **Not used.** Adds latency, adds nothing to the score. |
| Language detect | Text-processing endpoints | Use on first utterance to set language. Then **lock it** (§11). |

**Rate limits, Starter tier [V]:**

- `bulbul:v3` — 30 req/min, 30 concurrent
- `sarvam-30b` — 40 req/min
- STT WebSocket — 20 concurrent
- **WebSocket connections opened in a fast burst get rejected well below the concurrent ceiling. Space them ~300 ms apart.** This will look like a mystery outage during demo rehearsal if not handled.
- ₹100 free credits on signup. Top up before 10:30; do not discover an empty balance at 2 PM.

**Audio format trap [V]:** sample rate must be set to 8000 **both at connection time and on every chunk**. Mismatched rates produce garbled output that looks like a model failure and is not.

---

## 7. Data model (SQLite, single file, zero setup)

```
callers(caller_id TEXT PK, first_seen TS, last_seen TS, language TEXT, call_count INT)

payees(payee_id TEXT PK, caller_id TEXT, display_name TEXT,
       relationship TEXT NULL, masked_account TEXT)

corrections(id INTEGER PK, caller_id TEXT, entity_type TEXT,   -- 'payee' | 'amount'
            heard_text TEXT, corrected_to TEXT, resolved_id TEXT NULL,
            hit_count INT DEFAULT 1, created_at TS, last_used_at TS)

attempts(id INTEGER PK, call_sid TEXT, caller_id TEXT, state TEXT,
         raw_transcript TEXT, hypothesis TEXT, confidence REAL NULL,
         ledger_hit BOOL, gate_fired BOOL, created_at TS)

transfers(txn_id TEXT PK, call_sid TEXT, caller_id TEXT, payee_id TEXT,
          amount_paise INT, status TEXT,   -- 'pending'|'success'|'aborted'
          committed_at TS NULL, aborted_at TS NULL, abort_state TEXT NULL)
```

`attempts` is not optional bookkeeping — it is the table the measured number in M5 is computed from, and the measured number is the Impact evidence.

**Seed data:** exactly 3 payees for one hardcoded demo caller ID, plus 3 for a second caller ID. **[I]** Six rows. A hardcoded payee list is explicitly acceptable for the demo. **[V from Idea Library]**

---

## 8. The commit state machine

Deterministic. Plain Python. No LLM in the transition logic.

### 8.1 States

| State | Bot behaviour | Exits on |
|---|---|---|
| `GREET` | Isolated greeting message | always → `AWAIT_PAYEE` |
| `AWAIT_PAYEE` | Ask who the money is for | payee slot filled |
| `CONFIRM_PAYEE` | Read back name + masked account | yes → `AWAIT_AMOUNT` / no → `AWAIT_PAYEE` (narrowed) |
| `AWAIT_AMOUNT` | Ask how much | amount slot filled |
| `CONFIRM_AMOUNT` | Read back amount in words **and** digit-by-digit | yes → `FINAL_CONFIRM` / no → `AWAIT_AMOUNT` (narrowed) |
| `FINAL_CONFIRM` | Read back payee + amount together, ask to send | yes → `COMMITTING` |
| `COMMITTING` | Filler line while rail is polled | rail returns → `DONE` |
| `DONE` | Read txn confirmation, trigger SMS | end |
| `ABORTED` | State explicitly that nothing was sent | end |

### 8.2 Abort

The abort keyword (`"रुको"` / `"ruko"` / `"cancel"` / `"stop"`) is checked on **every** partial transcript in **every** state, including mid-readback, including during `COMMITTING` if the rail has not yet returned. Abort is handled by the audio layer, not the LLM — it must fire even if the LLM call is in flight.

**Acceptance:** saying the abort keyword at any point of the `CONFIRM_AMOUNT` readback stops TTS within 500 ms and lands in `ABORTED` with `transfers.status = 'aborted'` and no rail call made.

### 8.3 The narrowed re-ask

On gate failure, the bot does **not** repeat the same open question. It asks a narrower one:

- Amount gate fails → "Kya aapne paanch hazaar kaha ya pachaas hazaar?" (present the two nearest plausible parses)
- Amount gate fails twice → drop to digit entry: "Amount ek ek karke boliye. Pehla number?"
- Payee gate fails → enumerate: "Aapke teen payees hain. Sunita, Ramesh, ya Manoj?"

This is the behaviour the Voice Experience score is actually reading. Narrowing beats repeating.

### 8.4 The confidence gate — and its fallback

**Primary [?]:** if Saaras v3 streaming exposes a confidence score, gate the amount slot on it. Threshold to be tuned against the recorded corpus in M5, starting at 0.75.

**Fallback if no confidence signal is exposed** (decide by 11:00, do not deliberate later):

1. **Double-parse consistency.** Run slot extraction on the transcript twice with `temperature=0`, plus once on the `verbatim`-mode transcript. Disagreement on the amount → gate fires. This is cheap and works.
2. **Plausibility band.** Amounts outside ₹100–₹50,000 gate automatically.
3. **Round-number prior.** Remittances are overwhelmingly round. `4,973` is more likely a mis-hear of `5,000` than a real amount; gate and offer the round neighbour as the narrowed re-ask.

The fallback is not a downgrade. Stated well at demo time, "we do not trust a single ASR pass on a construction site, so we require two independent parses to agree before money moves" is a *stronger* answer than quoting a model confidence number.

---

## 9. The correction ledger — the differentiator

**Build this before you polish anything.** It is worth more rubric points than the audio quality.

### 9.1 Behaviour

On every payee or amount-phrase hypothesis:

1. Normalise the hypothesis (lowercase, strip punctuation, transliterate Devanagari → Latin for comparison).
2. Fuzzy-match against `corrections` **for this `caller_id` only**, `entity_type` matching.
3. Match at or above threshold (start at 85, `rapidfuzz.partial_ratio`) → resolve directly to `corrected_to` / `resolved_id`, **bypass the gate**, increment `hit_count`, set `last_used_at`.
4. No match → normal gate path. If the gate fires and the caller then corrects the value, **write a new `corrections` row** linking the mis-heard text to the confirmed value.

### 9.2 Governance (this is what makes it L4+ rather than a cache)

- Ledger entries are **scoped to one caller.** Never shared, never global. State this at demo time; a judge will ask.
- A ledger hit is **still read back.** It bypasses the *gate*, not the *confirmation*. Money never moves without a readback. Say this out loud.
- A caller can overwrite an entry by correcting again. Last correction wins; `hit_count` resets.
- Every ledger hit is logged in `attempts.ledger_hit = true`, which is how the M5 number is computed.

### 9.3 Acceptance test — this is the demo

```
Call 1: caller says "Sunita" → ASR returns "suneetha" → gate fires
        → narrowed re-ask → caller confirms Sunita
        → corrections row written: ("suneetha" → payee_id sunita)
Call 2: same caller_id, same utterance → ASR returns "suneetha"
        → ledger hit → resolves to Sunita first-try
        → no gate, no re-ask, straight to readback
```

If this passes end to end, Memory moves L2→L4 and Creativity moves L3→L4/L5. Nothing else in the build does that.

---

## 10. Indian numerals and readback

**Do the conversion deterministically in Python. Never delegate it to the LLM or to TTS preprocessing.** LLMs are unreliable at lakh/crore grouping and you cannot debug it live.

Two functions, both pure, both unit-tested before they touch audio:

```
parse_spoken_amount(text: str, lang: str) -> int   # returns paise
format_amount_for_speech(paise: int, lang: str) -> tuple[str, str]
    # returns (words_form, digits_form)
```

**Required test cases — these must pass before M4 is complete:**

| Input | `words_form` | `digits_form` |
|---|---|---|
| ₹5,000 | "paanch hazaar rupaye" | "paanch, zero, zero, zero" |
| ₹4,52,318 | "chaar lakh bavan hazaar teen sau atharah rupaye" | digit-by-digit |
| ₹100 | "sau rupaye" | "ek, zero, zero" |
| ₹12,50,000 | "baarah lakh pachaas hazaar rupaye" | digit-by-digit |
| "paanch hazaar" | → 500000 paise | |
| "5 thousand" | → 500000 paise | |
| "5k" | → 500000 paise | |
| "paanch hazaar paanch sau" | → 550000 paise | |

**Readback format for irreversible actions — say both forms:**

> "Paanch hazaar rupaye. Yaani, paanch, zero, zero, zero. Sunita ko. Bhejein?"

Words alone can be mis-heard the same way twice. Digits alone are unnatural. Both together is what banks do and it is what makes the confirmation loop actually load-bearing rather than decorative.

**Payee names** go through a Bulbul v3 pronunciation dictionary built at seed time from the six payee names. Prevents the TTS mangling the name it is asking the caller to confirm.

---

## 11. Voice scripts

Conventions applied throughout, non-negotiable:

- Greeting is an **isolated first-message block**, never embedded in the system prompt body
- **No exclamation marks. No em dashes. No ALL CAPS.** They distort TTS prosody.
- No meta-annotations, scenario numbers, or comments inside any prompt
- Language detected on first utterance, then **locked for the call.** Set `target_language_code` from the detected value; never hardcode it. Hardcoding is the most common way language lock silently fails.

**Greeting (separate message):**

> "Namaste. Paisa bhejne ke liye, batayiye kisko bhejna hai."

**System prompt — three sections only:**

1. **Role and scope.** You extract three things: who the money is for, how much, and whether the caller is confirming, correcting, or aborting. You do not decide anything. You return JSON.
2. **Output contract.** Strict JSON: `{payee_phrase, amount_phrase, intent}` where intent ∈ `{provide, confirm, correct, abort, unclear}`. No prose. No markdown fences.
3. **Language lock.** Respond in the language detected at call start. Proper nouns stay as spoken. Never switch to English mid-call.

**Fixed lines** (not LLM-generated — these are strings, so they cannot drift):

| Situation | Line |
|---|---|
| Payee readback | "{name} ko. Account {masked}. Sahi hai?" |
| Amount readback | "{words}. Yaani {digits}. Sahi hai?" |
| Final confirm | "{words} rupaye, {name} ko. Bhejein?" |
| Gate fired, amount | "Maine theek se nahi suna. Aapne {a} kaha ya {b}?" |
| Gate fired twice | "Amount ek ek karke boliye. Pehla number?" |
| Committing filler | "Bhej rahe hain. Ek second rukiye." |
| Success | "Ho gaya. {words} rupaye {name} ko bhej diye. SMS aa raha hai." |
| Abort | "Rok diya. Kuch nahi bheja gaya. Paisa aapke account mein hi hai." |
| Ledger hit (optional, Delight) | "{name}, jaise pichli baar." |

That last line is worth building. It is the audible proof that memory happened, and it costs one string.

---

## 12. Mocked rail

**Never wire a live payment rail.** **[V from Idea Library]** Say the word "mocked" in the first fifteen seconds of the demo, unprompted.

Three local FastAPI endpoints, in-process, no external dependency:

```
POST /rail/resolve_payee   {caller_id, payee_id}  -> {payee_id, name, masked_account}
POST /rail/transfer        {caller_id, payee_id, amount_paise, idempotency_key}
                                                  -> {txn_id, status:"pending"}
GET  /rail/status/{txn_id}                        -> {txn_id, status:"success"}  (after ~2s)
```

The 2-second pending window is deliberate: it is what the `COMMITTING` filler line exists to cover, and covering it gracefully is Delight evidence.

**Idempotency key** = `call_sid + payee_id + amount_paise`. Prevents a double-commit if the state machine is re-entered. A judge may try to trigger this.

**SMS receipt:** Twilio SMS to the caller's number. If SMS provisioning is blocked, log the receipt and read it aloud instead. Do not spend more than 15 minutes on SMS.

---

## 13. Milestones

Derived from actual event times. Each milestone has exact tasks, one acceptance test, a named fallback, and the rubric line it moves.

---

### M0 · 10:30–11:00 · De-risk the two unknowns (30 min, hard stop)

Run both spikes in parallel across two people. Nothing else starts until both resolve.

**Spike A — telephony.** Inbound call reaches the FastAPI webhook and bidirectional audio flows. Echo the caller's own audio back as proof.
**Spike B — confidence.** Send one recorded Hinglish clip to Saaras v3 streaming. Inspect the raw response payload for any confidence, score, or n-best field. Also timebox 15 minutes to reading what **Sarvam Conversations** is.

**Acceptance:** you can call a number and hear yourself echoed back, AND you have written down in this file whether §8.4 uses the primary gate or the fallback.

**If behind:** Spike A failing at 11:00 is the kill condition. Invoke §17. Spike B failing is not a blocker — default to the §8.4 fallback and move on.

**Rubric:** none directly. This is insurance.

---

### M1 · 11:00–12:00 · One ugly end-to-end transfer

Hardcode aggressively. One caller ID, one payee, no ledger, no gate, no abort.

- Twilio `<Stream>` → FastAPI → Saaras v3 (`codemix`) → Sarvam-30B slot extraction → Bulbul v3 readback → mocked rail → `DONE`
- SQLite created, `transfers` row written
- Greeting as isolated first message

**In parallel, non-blocking (one person, done by 11:30):** record the test corpus (§14). This has a hard deadline because tuning on laptop-mic audio and discovering the telephony codec at 3:30 PM is how this card fails. **[V from Idea Library]**

**Acceptance:** call the number, say "Sunita ko paanch hazaar bhejo," hear a readback, say "haan," get a `txn_id`. Once.

**If behind:** drop Sarvam-30B, regex the amount out of the transcript. The pipeline mattering more than the parsing quality at this stage.

**Rubric:** JTBD L1 → L3.

---

### M2 · 12:00–1:15 · State machine, abort, gate

- All nine states from §8.1 implemented as explicit Python, no LLM in transitions
- Abort keyword checked on every partial in every state, including mid-TTS
- Confidence gate (primary or fallback per M0) on the amount slot
- Narrowed re-ask, both tiers (§8.3)

**Acceptance:** three scripted runs — (a) clean commit, (b) deliberately mumbled amount triggers a narrowed re-ask rather than a guess, (c) abort spoken mid-readback stops TTS within 500 ms and commits nothing.

**If behind:** cut the second-tier digit-entry re-ask. Keep the first-tier narrowed re-ask and the abort. **Never cut the abort.**

**Rubric:** Voice Experience L2 → L4. JTBD L3 → L4.

---

### M3 · 1:15–2:30 · The correction ledger ← THE DIFFERENTIATOR

- `corrections` table wired per §9
- Normalise + transliterate + `rapidfuzz` match, caller-scoped
- Ledger hit bypasses gate, still reads back, logs `attempts.ledger_hit`
- Write a correction row whenever a gate failure is followed by a caller confirmation
- The "jaise pichli baar" line

**Acceptance:** §9.3, run twice with two different payee names, on two separate calls, unassisted.

**If behind:** this is the last thing to cut. If M2 overran, cut M4 entirely and protect this. A build with a ledger and mediocre numerals outscores a build with beautiful numerals and no ledger by roughly four weighted points.

**Rubric:** Memory L2 → L4/L5. Creativity L3 → L4/L5. Delight L2 → L4.

---

### M4 · 2:30–3:15 · Numerals, dual readback, language lock

- `parse_spoken_amount` and `format_amount_for_speech`, all §10 test cases green
- Dual readback (words + digits) on `CONFIRM_AMOUNT` and `FINAL_CONFIRM`
- Bulbul pronunciation dictionary seeded with the six payee names
- Language detection on first utterance, then locked; `target_language_code` set dynamically

**Acceptance:** ₹4,52,318 is spoken as "chaar lakh bavan hazaar teen sau atharah," not as four hundred fifty-two thousand. A caller who opens in Hindi is never answered in English.

**If behind:** cut the pronunciation dictionary and the ₹1L+ cases. Keep dual readback and correct lakh/hazaar grouping under ₹1,00,000, which covers every realistic remittance.

**Rubric:** Voice Experience L4 → L5.

---

### M5 · 3:15–3:45 · Measure it (do not skip this)

Run the full recorded corpus (§14) through the pipeline offline. Compute and write down:

1. Amount mis-heard rate, raw ASR, over telephony audio
2. **Of those mis-hears, how many were caught by the gate before commit** ← the headline number
3. Wrong-transfer rate (mis-heard AND committed). Target: zero.
4. First-try resolution rate, call 1 vs call 2, with the ledger active ← the Memory number
5. Median time from call start to commit

**Acceptance:** five numbers written into the demo one-pager. Number 3 is zero.

**If behind:** compute numbers 2 and 3 only. Those two carry the pitch. Note that the terms include a verification-consent clause **[V]** — metric claims may be spot-checked, so do not round in your favour.

**Rubric:** Impact L3 → L4/L5. JTBD evidence for the L4 band.

---

### M6 · 3:45–4:30 · Harden and submit (submit by 4:20)

- Reset script: wipe `attempts` and `transfers`, preserve seeded payees, **optionally preserve or clear `corrections` depending on which demo beat you are running.** Have both.
- Record the full 2-minute demo as a fallback video, on the actual venue floor with actual venue noise
- Three consecutive clean runs, unassisted, timed
- Submission assets: repo link, one-pager (workflow, integration surface, recording consent and redaction policy, who can hear a recording of someone moving money, deploy-or-pilot verdict, why Voice Experience was declared)
- Flag "borderline starting point" in notes if there is any ambiguity about origin
- **Submit at 4:20. Not 4:29.**

**Acceptance:** submitted, and the fallback video exists and plays.

**If behind:** cut the one-pager to five bullets. Never cut the fallback video.

---

### M7 · 4:30–5:30 · Two timed rehearsals

Full 3-minute run, twice, on the floor, with a stranger playing the judge. Second rehearsal must land inside 3:00 without rushing the cold open.

Charge everything. Wired headset ready. Hotspot on. Confirm the phone that will be handed to the judge is unlocked and dialled.

---

## 14. Test corpus (recorded by 11:30, no exceptions)

Recorded **over an actual phone call**, not a laptop microphone. Minimum 20 clips:

| Count | Content |
|---|---|
| 6 | Amounts in Hinglish, mixed forms: "paanch hazaar", "5 thousand", "das hazaar paanch sau", "5k" |
| 4 | The same amounts with construction noise or a crowd behind the speaker |
| 4 | Payee names, Indian proper nouns, at least two easily confusable |
| 2 | One deliberate dropped second mid-utterance |
| 2 | Caller rambling before getting to the amount |
| 2 | Abort spoken mid-sentence |

Two different speakers if possible. Store as 8 kHz mulaw to match the production path.

This corpus is what M5 measures and what you tune the gate threshold against. Laptop-microphone audio will lie to you about accuracy all morning. **[V from Idea Library]**

---

## 15. Non-goals — do not build these

- A real or sandboxed payment rail of any kind
- Any language other than Hindi and Hinglish
- Payee onboarding, account linking, or KYC
- Any web UI, dashboard, or admin screen
- Authentication, user accounts, or session management beyond `caller_id`
- More than six seeded payees
- Doc AI, Dubbing, translation, or any second Sarvam capability
- Speaker verification or fraud detection
- Multi-turn conversational chit-chat outside the transfer flow
- Deployment to anything other than the build laptop plus a tunnel

---

## 16. Parking lot

Recorded so they stop occupying attention. None of these enter the critical path without an explicit rescope.

- Relationship-based payee reference ("ghar bhejo", "maa ko") — cheapest genuine add, only if M4 finishes early
- Voice callback to the recipient in their language ("Sujit ne aapko paanch hazaar bheje hain")
- Odia or Malayalam support
- Scheduled or recurring transfers
- Balance enquiry
- Ledger decay for stale corrections
- Confidence-threshold auto-tuning from `attempts`
- A web view of the ledger for the demo

---

## 17. Kill conditions and stop conditions

| Condition | Time | Action |
|---|---|---|
| No inbound call reaching the webhook | 11:00 | **Kill the telephony path.** Fall back to a browser-mic demo with a codec-degraded audio filter and say so honestly. Voice Experience ceiling drops to L3. The build survives. |
| Confidence signal unavailable | 11:00 | Switch to §8.4 fallback. Do not deliberate further. |
| M1 not passing | 12:15 | Strip Sarvam-30B, regex the slots. Ship the pipeline. |
| M2 not passing | 1:30 | Cut tier-two re-ask. Abort stays. |
| M3 not started | 2:00 | **Stop M2 polish immediately and start M3.** The ledger outscores everything remaining. |
| Any milestone overruns by >20 min | any | Take the named fallback. Do not extend. |
| After 3:45 | 3:45 | **Feature freeze.** No new code except bug fixes to the golden path. |

---

## 18. Demo script — 3 minutes

Format per the handbook: 30 sec context, 30 sec workflow, 2 min live. **[V]**

**0:00–0:30 · Business context.** No tech. No jargon.
> Every month, a construction worker in Kochi sends money home to Odisha. He has a feature phone and no data. So he hands cash to an agent at the site gate and pays two to five per cent for the privilege of someone else reading the screen. That cut is the number we are here to beat.

**0:30–1:00 · Workflow today.** Name the friction and the metric. State the baseline from M5. Say the word **mocked** here, once, unprompted.

**1:00–3:00 · Live demo.** Four beats, in this order. Hand the judge the phone.

| Beat | What happens | What it proves |
|---|---|---|
| 1 | Judge calls from the floor, says an amount in Hindi with English digits. Correct readback in words and digits. Commits. SMS arrives. | **JTBD** + **Voice Experience** |
| 2 | Judge says a payee name. Gate fires. System asks a narrower question instead of guessing. Judge corrects it. | **Voice Experience** |
| 3 | **Judge hangs up. Calls back. Says the same name. It resolves first-try.** | **Memory** + **Creativity** |
| 4 | Judge says the abort word mid-readback. Everything stops. Nothing moved. | **Delight** |

Close on the M5 number, not the stack: mis-hear rate, catch rate, wrong-transfer rate of zero.

**Beat 3 is the demo.** Beats 1, 2 and 4 depend partly on luck with the audio. Beat 3 does not. If time is collapsing, sacrifice beat 1 and open on beat 2.

**If the live run drops:** narrate the intended behaviour, cut to the fallback video, keep moving. Do not spend thirty seconds apologising. **[V: handbook explicitly says recovery matters]**

---

## 19. Evidence map

| Rubric parameter | The exact moment that earns it |
|---|---|
| Job-to-be-done completion | Beat 1 committing with a `txn_id` and an SMS, plus three unassisted runs in M6 |
| Memory and Context | Beat 3 — declared framing is cross-session correction retention, keyed to caller identity, caller-scoped |
| Creativity | The ledger reframing accuracy as learned-per-caller rather than model-determined, stated in one sentence during beat 3 |
| Impact | The M5 numbers against the 2–5% agent-cut baseline, stated at 0:30 and again at close |
| Delight | Beat 4 — abort landing clean and the caller being explicitly told nothing moved |
| **Voice Experience (declared)** | Beat 2 — narrowband telephony, room noise, code-switched amount, narrowed re-ask instead of a guess |

Say "we are declaring Voice Experience" out loud. Do not make the judge infer it.

---

## 20. Pre-mortem

It is 5:30 PM and this failed. Most likely reasons, in order:

1. **No working phone number.** Mitigated by pre-event verification and the §17 browser-mic fallback.
2. **Telephony consumed the day and the ledger was never built** — so you shipped the Idea Library card as written and scored ~34. Mitigated by the hard 2:00 PM trigger in §17.
3. **Room noise broke every live beat on stage.** Mitigated by the fallback video recorded on the actual floor and by beat 3 not depending on clean audio.
4. **A judge asked whether real money moved.** Mitigated by saying "mocked" at 0:45.
5. **Origin questioned.** Mitigated by building from zero on the floor and flagging anything borderline in the notes.

---

## 21. Team split

| Owner | Owns | Never blocked on |
|---|---|---|
| A — telephony/audio | Twilio, Media Streams, Saaras and Bulbul WebSockets, barge-in plumbing | Anything downstream of the transcript |
| B — logic | State machine, gate, ledger, SQLite, mocked rail | Audio quality |
| C — product (Kaustubh) | Corpus recording, numeral functions, all voice scripts, M5 measurement, one-pager, demo | Both of the above |

C owns the numeral functions specifically because they are pure, testable, and require zero integration — they can be written and unit-tested while the audio layer is still broken.

---

## 22. Next single action

**Before the event:** confirm a phone number that rings from an Indian mobile and reaches a webhook. Nothing in this document survives that being false.

**At 10:30 AM:** open M0. Both spikes in parallel. Write the §8.4 decision into this file by 11:00.
