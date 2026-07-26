from app.core.gate import gate_amount
from app.core.state_machine import CallSession, Payee, State, is_abort

SUNITA = Payee("payee-sunita", "Sunita", "XXXX-XXXX-4521")
RAMESH = Payee("payee-ramesh", "Ramesh", "XXXX-XXXX-7789")
MANOJ = Payee("payee-manoj", "Manoj", "XXXX-XXXX-1102")


def make_session():
    return CallSession(call_sid="CA1", caller_id="demo-caller-1", payees=[SUNITA, RAMESH, MANOJ])


def test_clean_commit_run():
    s = make_session()
    turn = s.greet()
    assert turn.state == State.AWAIT_PAYEE

    turn = s.submit_payee(SUNITA, ledger_hit=False)
    assert turn.state == State.CONFIRM_PAYEE
    assert "Sunita" in turn.line

    turn = s.confirm_payee(True)
    assert turn.state == State.AWAIT_AMOUNT

    amount_paise = 5000 * 100
    gate = gate_amount(amount_paise, confidence=0.95, confidence_threshold=0.75)
    assert gate.passed
    turn = s.submit_amount(amount_paise, gate.passed)
    assert turn.state == State.CONFIRM_AMOUNT
    assert "paanch hazaar rupaye" in turn.line

    turn = s.confirm_amount(True)
    assert turn.state == State.FINAL_CONFIRM

    turn = s.final_confirm(True)
    assert turn.state == State.COMMITTING

    turn = s.committed("txn_abc123")
    assert turn.state == State.DONE
    assert s.txn_id == "txn_abc123"


def test_mumbled_amount_triggers_narrowed_reask_not_a_guess():
    s = make_session()
    s.greet()
    s.submit_payee(SUNITA)
    s.confirm_payee(True)

    # "4973" mis-heard amount: fails plausibility/round-number fallback gate
    heard_paise = 4973 * 100
    gate = gate_amount(heard_paise, confidence=None)
    assert not gate.passed
    turn = s.submit_amount(heard_paise, gate.passed, candidates=gate.candidates)

    assert turn.state == State.AWAIT_AMOUNT
    assert s.amount_paise is None  # never silently accepted as a guess
    assert "kaha ya" in turn.line
    assert "paanch hazaar" in turn.line  # round-neighbour offered as one of the two options


def test_amount_gate_fails_twice_drops_to_digit_entry():
    s = make_session()
    s.greet()
    s.submit_payee(SUNITA)
    s.confirm_payee(True)

    bad_paise = 99 * 100  # below plausibility band
    gate1 = gate_amount(bad_paise, confidence=None)
    s.submit_amount(bad_paise, gate1.passed, candidates=gate1.candidates)

    gate2 = gate_amount(bad_paise, confidence=None)
    turn = s.submit_amount(bad_paise, gate2.passed, candidates=gate2.candidates)

    assert s.digit_entry_mode is True
    assert turn.line == "Amount ek ek karke boliye. Pehla number?"


def test_abort_mid_amount_readback_stops_and_commits_nothing():
    s = make_session()
    s.greet()
    s.submit_payee(SUNITA)
    s.confirm_payee(True)
    gate = gate_amount(5000 * 100, confidence=0.9)
    s.submit_amount(5000 * 100, gate.passed)
    assert s.state == State.CONFIRM_AMOUNT

    assert is_abort("ruko ruko")
    turn = s.abort()

    assert turn.state == State.ABORTED
    assert s.abort_state == State.CONFIRM_AMOUNT
    assert s.txn_id is None


def test_abort_keyword_detection():
    assert is_abort("ruko")
    assert is_abort("cancel please")
    assert is_abort("STOP")
    assert not is_abort("paanch hazaar bhejo")


def test_payee_gate_failure_enumerates_candidates_not_repeat_question():
    s = make_session()
    s.greet()
    turn = s.submit_payee(None)
    assert turn.state == State.AWAIT_PAYEE
    assert "Sunita" in turn.line and "Ramesh" in turn.line and "Manoj" in turn.line
    assert s.payee_gate_fail_count == 1
