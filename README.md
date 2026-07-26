# AWAAZ-PAY

Voice remittance IVR per `IDEA_SCOPE.md`. Telephony provider is **Vobiz**
(swapped in for the scope doc's Twilio default — see the plan notes below),
Saaras v3 for STT, Bulbul v3 for TTS, Sarvam-30B for slot extraction only.

## §8.4 decision, written down as the scope doc requires

Saaras v3's real-world integration (the pipecat-ai Sarvam STT service) parses
only `transcript` and `language_code` off transcript messages — no
confidence/score field. This build therefore ships on the **fallback gate**
(double-parse consistency + plausibility band ₹100–₹50,000 + round-number
prior) by default. `app/core/gate.py` still checks for a confidence value
opportunistically and prefers it if Saaras ever returns one, but treat the
fallback as the real mechanism when writing the demo script.

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in VOBIZ_AUTH_ID, VOBIZ_AUTH_TOKEN, SARVAM_API_KEY
```

## Run

```bash
./.venv/bin/uvicorn app.main:app --port 8811
```

This seeds the DB (6 payees / 2 demo callers) on startup. Sanity-check the
mocked rail without any audio involved:

```bash
curl -X POST localhost:8811/rail/resolve_payee -H "Content-Type: application/json" \
  -d '{"caller_id":"demo-caller-1","payee_id":"payee-sunita"}'
```

## Wire up a real call (Vobiz + ngrok)

1. `ngrok http 8811` and copy the `https://...ngrok...` URL into `PUBLIC_BASE_URL` in `.env`, restart uvicorn.
2. In the Vobiz console, create an Application with **Answer URL** = `<ngrok-url>/answer`.
3. Point your Vobiz number at that Application.
4. Call the number. First call is also the echo-back/schema-confirmation
   spike — watch the server log for `Unrecognized inbound media frame shape`;
   if that appears, the live `media` event JSON doesn't match
   `_extract_inbound_payload` in `app/telephony/bridge.py` and needs a
   one-line fix once the real payload shape is visible in the log.

## Tests

```bash
./.venv/bin/python3 -m pytest tests/ -q
```

20 tests: numeral parsing/formatting (§10 required cases), state machine
(abort-at-any-state, narrowed re-ask, digit-entry fallback), and the ledger
acceptance sequence (§9.3: miss → correction written → same utterance
resolves first-try on the next call, scoped per-caller).

## Demo utilities

```bash
./.venv/bin/python3 -m scripts.reset_demo                    # wipe attempts/transfers, keep payees + corrections
./.venv/bin/python3 -m scripts.reset_demo --clear-corrections # also wipe corrections, for the "call 1" beat
./.venv/bin/python3 -m scripts.measure                        # print the M5 numbers from attempts/transfers
```

## What's not implemented / needs the builder's own accounts

- `corpus/` is empty — the 20-clip recorded corpus (§14) needs a real phone
  call to produce; `corpus/README.md` has the exact manifest and format.
- SMS receipt is not wired (no dedicated Vobiz SMS API found in docs) — the
  success line is read aloud per the scope doc's own stated fallback (§12).
  WhatsApp send is a documented but non-critical upgrade if wanted later.
- Bulbul pronunciation-dictionary seeding (`app/sarvam/tts.py:seed_pronunciation_dict`)
  calls an assumed endpoint and fails soft (returns `None`) if it's wrong —
  cuttable per §13 M4's own "if behind" clause.
