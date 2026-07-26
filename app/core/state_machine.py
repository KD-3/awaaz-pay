"""The commit state machine (§8). Deterministic, plain Python. No LLM in the
transition logic - Sarvam-30B only ever fills slots upstream of this module;
nothing it returns can trigger a state transition on its own.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.core import scripts


class State(str, Enum):
    GREET = "GREET"
    AWAIT_PAYEE = "AWAIT_PAYEE"
    CONFIRM_PAYEE = "CONFIRM_PAYEE"
    AWAIT_AMOUNT = "AWAIT_AMOUNT"
    CONFIRM_AMOUNT = "CONFIRM_AMOUNT"
    FINAL_CONFIRM = "FINAL_CONFIRM"
    COMMITTING = "COMMITTING"
    DONE = "DONE"
    ABORTED = "ABORTED"


ABORT_KEYWORDS = ["ruko", "रुको", "cancel", "stop", "rok do", "rok"]
_ABORT_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in ABORT_KEYWORDS) + r")\b", re.IGNORECASE)


def is_abort(text: str) -> bool:
    """Checked on every partial transcript in every state, including mid-TTS.
    Handled at the audio layer, not gated on any LLM call being in flight."""
    return bool(_ABORT_RE.search(text or ""))


@dataclass
class Payee:
    payee_id: str
    display_name: str
    masked_account: str


@dataclass
class BotTurn:
    state: State
    line: str
    ledger_hit: bool = False


@dataclass
class CallSession:
    call_sid: str
    caller_id: str
    payees: list[Payee]
    state: State = State.GREET
    selected_payee: Payee | None = None
    amount_paise: int | None = None
    amount_candidates: tuple[int, int] | None = None
    amount_gate_fail_count: int = 0
    payee_gate_fail_count: int = 0
    digit_entry_mode: bool = False
    txn_id: str | None = None
    abort_state: State | None = None

    def greet(self) -> BotTurn:
        self.state = State.AWAIT_PAYEE
        return BotTurn(self.state, scripts.GREETING)

    def submit_payee(self, resolved: Payee | None, ledger_hit: bool = False) -> BotTurn:
        """Called after the ledger/gate have already tried to resolve the payee
        phrase. `resolved` is None if the gate fired (no confident match)."""
        if resolved is not None:
            self.selected_payee = resolved
            self.state = State.CONFIRM_PAYEE
            line = scripts.payee_readback(resolved.display_name, resolved.masked_account)
            if ledger_hit:
                line = f"{scripts.ledger_hit_line(resolved.display_name)} {line}"
            return BotTurn(self.state, line, ledger_hit=ledger_hit)

        self.payee_gate_fail_count += 1
        self.state = State.AWAIT_PAYEE
        names = [p.display_name for p in self.payees]
        return BotTurn(self.state, scripts.payee_enumerate_line(names))

    def confirm_payee(self, yes: bool) -> BotTurn:
        if yes:
            self.state = State.AWAIT_AMOUNT
            return BotTurn(self.state, scripts.AWAIT_AMOUNT_LINE)
        self.selected_payee = None
        self.state = State.AWAIT_PAYEE
        names = [p.display_name for p in self.payees]
        return BotTurn(self.state, scripts.payee_enumerate_line(names))

    def submit_amount(self, amount_paise: int, gate_passed: bool, candidates: tuple[int, int] | None = None) -> BotTurn:
        if gate_passed:
            self.amount_paise = amount_paise
            self.amount_gate_fail_count = 0
            self.digit_entry_mode = False
            self.state = State.CONFIRM_AMOUNT
            from app.core.numerals import format_amount_for_speech

            words, digits = format_amount_for_speech(amount_paise)
            return BotTurn(self.state, scripts.amount_readback(words, digits))

        self.amount_gate_fail_count += 1
        self.state = State.AWAIT_AMOUNT

        if self.amount_gate_fail_count >= 2:
            self.digit_entry_mode = True
            return BotTurn(self.state, scripts.GATE_FIRED_TWICE_LINE)

        from app.core.numerals import format_amount_for_speech

        a_paise, b_paise = candidates or (amount_paise, amount_paise)
        a_words, _ = format_amount_for_speech(a_paise)
        b_words, _ = format_amount_for_speech(b_paise)
        self.amount_candidates = (a_paise, b_paise)
        return BotTurn(self.state, scripts.gate_fired_amount_line(a_words, b_words))

    def confirm_amount(self, yes: bool) -> BotTurn:
        if yes:
            self.state = State.FINAL_CONFIRM
            from app.core.numerals import format_amount_for_speech

            words, _ = format_amount_for_speech(self.amount_paise)
            return BotTurn(self.state, scripts.final_confirm_line(words, self.selected_payee.display_name))
        self.amount_paise = None
        self.state = State.AWAIT_AMOUNT
        return BotTurn(self.state, scripts.AWAIT_AMOUNT_LINE)

    def final_confirm(self, yes: bool) -> BotTurn:
        if yes:
            self.state = State.COMMITTING
            return BotTurn(self.state, scripts.COMMITTING_FILLER)
        self.state = State.AWAIT_AMOUNT
        self.amount_paise = None
        return BotTurn(self.state, scripts.AWAIT_AMOUNT_LINE)

    def committed(self, txn_id: str) -> BotTurn:
        self.txn_id = txn_id
        self.state = State.DONE
        from app.core.numerals import format_amount_for_speech

        words, _ = format_amount_for_speech(self.amount_paise)
        return BotTurn(self.state, scripts.success_line(words, self.selected_payee.display_name))

    def abort(self) -> BotTurn:
        self.abort_state = self.state
        self.state = State.ABORTED
        return BotTurn(self.state, scripts.ABORT_LINE)
