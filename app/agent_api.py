"""HTTP tool endpoints for a Sarvam Agents-hosted voice agent (§5.1's governing
rule, adapted): the agent's LLM decides *when* to call these, but the actual
payee resolution, ledger lookups/writes, amount gating, and money movement
all happen here, in plain deterministic Python - not in the agent's prompt.
The agent only ever sees pass/fail + data back from these calls; it cannot
resolve a payee, gate an amount, or commit a transfer on its own.

No auth on these routes - acceptable for a hackathon demo hitting a private
tunnel URL only Sarvam's agent knows, not for anything real.

Pydantic model fields here use `typing.Optional`/`typing.List` rather than the
`X | None` / `list[X]` syntax - pydantic evaluates annotations at runtime and
that syntax isn't supported on the Python 3.9 interpreter this runs on.
"""
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core import ledger
from app.core.gate import gate_amount
from app.core.numerals import format_amount_for_speech, parse_spoken_amount
from app.core.state_machine import Payee
from app.db import get_connection

logger = logging.getLogger("awaazpay.agent_api")

router = APIRouter(prefix="/agent", tags=["agent-tools"])


def _load_payees(conn, caller_id):
    rows = conn.execute(
        "SELECT payee_id, display_name, masked_account FROM payees WHERE caller_id = ?",
        (caller_id,),
    ).fetchall()
    return [Payee(r["payee_id"], r["display_name"], r["masked_account"]) for r in rows]


class ResolvePayeeRequest(BaseModel):
    caller_id: str
    payee_phrase: str


class ResolvePayeeResponse(BaseModel):
    resolved: bool
    payee_id: Optional[str] = None
    name: Optional[str] = None
    masked_account: Optional[str] = None
    ledger_hit: bool = False
    candidates_spoken: str = ""  # ready-to-read-aloud enumeration, e.g. "Sunita, Ramesh, ya Manoj"


def _spoken_list(names: list) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f", ya {names[-1]}"


@router.post("/resolve_payee", response_model=ResolvePayeeResponse)
def resolve_payee(req: ResolvePayeeRequest) -> ResolvePayeeResponse:
    logger.info("resolve_payee REQUEST: caller_id=%r payee_phrase=%r", req.caller_id, req.payee_phrase)
    conn = get_connection()
    try:
        payees = _load_payees(conn, req.caller_id)
        resolved, ledger_hit = ledger.resolve_payee(conn, req.caller_id, req.payee_phrase, payees)
        conn.commit()
    finally:
        conn.close()

    if resolved is None:
        response = ResolvePayeeResponse(resolved=False, candidates_spoken=_spoken_list([p.display_name for p in payees]))
    else:
        response = ResolvePayeeResponse(
            resolved=True,
            payee_id=resolved.payee_id,
            name=resolved.display_name,
            masked_account=resolved.masked_account,
            ledger_hit=ledger_hit,
        )
    logger.info("resolve_payee RESPONSE: %r (payees on file for this caller_id: %s)",
                response, [p.display_name for p in payees])
    return response


class RecordCorrectionRequest(BaseModel):
    caller_id: str
    heard_text: str
    corrected_to: str
    resolved_id: str


@router.post("/record_correction")
def record_correction(req: RecordCorrectionRequest) -> dict:
    """Call after the caller confirms who they actually meant, whether that's
    a fresh direct match or a correction following a narrowed re-ask (§9.1
    step 4). Writes the ledger entry that makes the next call's identical
    mis-hear resolve first-try."""
    conn = get_connection()
    try:
        ledger.record_correction(conn, req.caller_id, "payee", req.heard_text, req.corrected_to, req.resolved_id)
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}


class CheckAmountRequest(BaseModel):
    amount_phrase: str
    language: str = "hi"
    second_amount_phrase: Optional[str] = None


class CheckAmountResponse(BaseModel):
    amount_paise: int
    passed: bool
    words_form: str
    digits_form: str
    candidate_word_a: str = ""
    candidate_word_b: str = ""


@router.post("/check_amount", response_model=CheckAmountResponse)
def check_amount(req: CheckAmountRequest) -> CheckAmountResponse:
    """Amount parsing and the confidence gate are both deterministic Python
    (§8.4, §10) - the agent passes the raw spoken phrase, never a
    pre-parsed number, so this function is the only thing that decides what
    the amount actually is and whether it's trustworthy enough to read back."""
    amount_paise = parse_spoken_amount(req.amount_phrase, req.language)
    second_paise = (
        parse_spoken_amount(req.second_amount_phrase, req.language) if req.second_amount_phrase else None
    )
    gate = gate_amount(amount_paise, second_parse_paise=second_paise)
    words, digits = format_amount_for_speech(amount_paise)

    candidate_word_a = candidate_word_b = ""
    if not gate.passed and gate.candidates:
        candidate_word_a = format_amount_for_speech(gate.candidates[0])[0]
        candidate_word_b = format_amount_for_speech(gate.candidates[1])[0]

    return CheckAmountResponse(
        amount_paise=amount_paise, passed=gate.passed, words_form=words, digits_form=digits,
        candidate_word_a=candidate_word_a, candidate_word_b=candidate_word_b,
    )
