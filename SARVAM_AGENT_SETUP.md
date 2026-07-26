# AWAAZ-PAY — Sarvam Agents console setup

Our backend is already reachable at:
`https://wales-filters-baltimore-innocent.trycloudflare.com`

(if the tunnel gets restarted, this URL changes — check with me before wiring tools if a call isn't reaching the backend)

## HTTP tools to create (Custom tools → HTTP)

For each tool: set "When should this tool run?" to **During conversation**. Paste the cURL command in step 2 (it auto-fills method/URL/headers/body). Fill in step 3 ("What the agent gets back") and the "Save reply into variables" list exactly as given — the saved variables are what later states reference as `{{name}}`, `{{masked_account}}`, etc.

### 1. `resolve_payee`
Description: "Looks up whether the name the caller said matches one of their saved payees."

cURL:
```
curl -X POST https://wales-filters-baltimore-innocent.trycloudflare.com/agent/resolve_payee \
  -H "Content-Type: application/json" \
  -d '{"caller_id": "demo-caller-1", "payee_phrase": "{{payee_phrase}}"}'
```
What the agent gets back: `resolved={{resolved}}, name={{name}}, masked_account={{masked_account}}, ledger_hit={{ledger_hit}}, candidates={{candidate_names}}`
Save into variables: `resolved`, `payee_id`, `name`, `masked_account`, `ledger_hit`, `candidate_names`

### 2. `record_correction`
Description: "Saves which payee the caller actually meant, so the same mis-hearing resolves instantly next call."

cURL:
```
curl -X POST https://wales-filters-baltimore-innocent.trycloudflare.com/agent/record_correction \
  -H "Content-Type: application/json" \
  -d '{"caller_id": "demo-caller-1", "heard_text": "{{heard_text}}", "corrected_to": "{{corrected_to}}", "resolved_id": "{{resolved_id}}"}'
```
What the agent gets back: `ok={{ok}}`
No variables need saving.

### 3. `check_amount`
Description: "Parses the amount the caller said and checks whether it's trustworthy enough to act on."

cURL:
```
curl -X POST https://wales-filters-baltimore-innocent.trycloudflare.com/agent/check_amount \
  -H "Content-Type: application/json" \
  -d '{"amount_phrase": "{{amount_phrase}}", "language": "hi"}'
```
What the agent gets back: `passed={{passed}}, words_form={{words_form}}, digits_form={{digits_form}}, candidates={{candidate_words}}`
Save into variables: `amount_paise`, `passed`, `words_form`, `digits_form`, `candidate_words`

### 4. `commit_transfer`
Description: "Actually sends the money. Only call this after the caller has confirmed both the payee and the amount."

cURL:
```
curl -X POST https://wales-filters-baltimore-innocent.trycloudflare.com/rail/transfer \
  -H "Content-Type: application/json" \
  -d '{"caller_id": "demo-caller-1", "payee_id": "{{payee_id}}", "amount_paise": {{amount_paise}}, "idempotency_key": "{{call_id}}"}'
```
What the agent gets back: `txn_id={{txn_id}}, status={{status}}`
Save into variables: `txn_id`, `status`

**Note on `{{call_id}}`**: if the platform exposes a built-in per-call/session ID variable, use that for `idempotency_key` instead — check the "@ to insert a field" picker for something like `call_id` or `session_id` provided by the platform itself, rather than one of our tool's saved variables.

## Global instructions

```
You help a caller send money to someone in Hindi or Hinglish. You never
decide on your own whether a name or amount is correct - you always call the
matching tool and base your next line only on what it returns. You never
say a transfer has happened unless commit_transfer returned a txn_id. No
exclamation marks, no ALL CAPS. Keep responses short and match the caller's
language.
```

## States

**GREET** (entry / greeting message)
> "Namaste. Paisa bhejne ke liye, batayiye kisko bhejna hai."
→ AWAIT_PAYEE

**AWAIT_PAYEE**
- Instructions: "Ask who the money is for if not already said. When the caller names someone, call `resolve_payee` with exactly what they said as `payee_phrase`. If `resolved` is true, go to CONFIRM_PAYEE. If false, read the `candidate_names` back as a choice (e.g. 'Aapke teen payees hain: X, Y, ya Z?') and stay in this state."
- Tools: resolve_payee
→ CONFIRM_PAYEE, AWAIT_PAYEE

**CONFIRM_PAYEE**
- Instructions: "Say '{name} ko. Account {masked_account}. Sahi hai?' using the values from the last resolve_payee call. If the caller confirms yes, call `record_correction` with heard_text = what they originally said, corrected_to = the resolved name, resolved_id = the payee_id (this is safe to call even on a direct match - it's how the ledger learns). Then go to AWAIT_AMOUNT. If the caller says no or names someone else, go back to AWAIT_PAYEE."
- Tools: record_correction
→ AWAIT_AMOUNT, AWAIT_PAYEE

**AWAIT_AMOUNT**
- Instructions: "Ask how much to send if not already said. Call `check_amount` with exactly what the caller said as `amount_phrase`. If `passed` is true, go to CONFIRM_AMOUNT. If false, ask 'Maine theek se nahi suna. Aapne {candidate_words[0]} kaha ya {candidate_words[1]}?' and stay here."
- Tools: check_amount
→ CONFIRM_AMOUNT, AWAIT_AMOUNT

**CONFIRM_AMOUNT**
- Instructions: "Say '{words_form}. Yaani {digits_form}. Sahi hai?' from the last check_amount call. If yes, go to FINAL_CONFIRM. If no, go back to AWAIT_AMOUNT."
→ FINAL_CONFIRM, AWAIT_AMOUNT

**FINAL_CONFIRM**
- Instructions: "Say '{words_form}, {name} ko. Bhejein?' If the caller confirms, call `commit_transfer` with the resolved payee_id and amount_paise, using the call id as idempotency_key. Then go to DONE. If they say stop/cancel/ruko, go to ABORTED without calling any tool."
- Tools: commit_transfer
→ DONE, ABORTED

**DONE**
> "Ho gaya. {words_form} {name} ko bhej diye."

**ABORTED**
> "Rok diya. Kuch nahi bheja gaya. Paisa aapke account mein hi hai."

## Abort handling
Add "ruko", "cancel", "stop" as recognized anywhere in global instructions:
"If the caller says ruko, cancel, or stop at any point, immediately go to
ABORTED without calling commit_transfer, regardless of current state."
