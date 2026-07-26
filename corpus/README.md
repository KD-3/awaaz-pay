# Test corpus (§14)

This corpus must be recorded **over an actual phone call** into the running
system (or at minimum through a real phone's mic into a recorder), not a
laptop microphone — laptop-mic audio does not reproduce the 8kHz mulaw
telephony codec and will lie about accuracy. This is the one artifact in the
build that needs the builder's own phone; it can't be produced in this
session.

## Manifest format

Each recorded clip gets an entry in `corpus/manifest.json`:

```json
{
  "file": "clips/amount_01_paanch_hazaar.wav",
  "kind": "amount",
  "expected_amount_paise": 500000,
  "notes": "clean, no noise"
}
```

or for payee clips:

```json
{
  "file": "clips/payee_01_sunita.wav",
  "kind": "payee",
  "expected_payee_id": "payee-sunita",
  "notes": "confusable with Sunita/Suneetha"
}
```

`scripts/measure.py` looks for an `asr_hypothesis_paise` (or
`asr_hypothesis_payee_id`) field added to each clip's entry after running it
through Saaras v3 batch STT + the pipeline offline — that scoring pass isn't
implemented here since there's no audio yet to run it against; wire it once
clips exist by looping the manifest through `app.core.numerals.parse_spoken_amount`
/ `app.core.ledger.resolve_payee` and filling in the hypothesis fields.

## Required manifest (minimum 20 clips, per §14)

| Count | Content |
|---|---|
| 6 | Amounts in Hinglish, mixed forms: "paanch hazaar", "5 thousand", "das hazaar paanch sau", "5k" |
| 4 | The same amounts with construction noise or a crowd behind the speaker |
| 4 | Payee names, Indian proper nouns, at least two easily confusable |
| 2 | One deliberate dropped second mid-utterance |
| 2 | Caller rambling before getting to the amount |
| 2 | Abort spoken mid-sentence |

Two different speakers if possible. Store as 8kHz mulaw (`.wav`, mono,
mulaw-encoded, 8000 Hz) to match the production path — e.g. via `sox`:

```
sox input.wav -r 8000 -c 1 -e mu-law clips/amount_01_paanch_hazaar.wav
```

Place clip files under `corpus/clips/` (gitignored if this repo is pushed
anywhere with real recordings of real names/numbers — see the one-pager's
recording consent and redaction policy, §M6).
