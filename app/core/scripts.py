"""Fixed voice-script strings (§11). These are plain strings, not LLM-generated,
so they cannot drift. Greeting is an isolated first-message block."""

GREETING = "Namaste. Paisa bhejne ke liye, batayiye kisko bhejna hai."

AWAIT_AMOUNT_LINE = "Kitna bhejna hai?"

GATE_FIRED_TWICE_LINE = "Amount ek ek karke boliye. Pehla number?"

COMMITTING_FILLER = "Bhej rahe hain. Ek second rukiye."

ABORT_LINE = "Rok diya. Kuch nahi bheja gaya. Paisa aapke account mein hi hai."


def payee_readback(name: str, masked_account: str) -> str:
    return f"{name} ko. Account {masked_account}. Sahi hai?"


def amount_readback(words_form: str, digits_form: str) -> str:
    return f"{words_form}. Yaani {digits_form}. Sahi hai?"


def final_confirm_line(words_form: str, name: str) -> str:
    return f"{words_form}, {name} ko. Bhejein?"


def gate_fired_amount_line(a_words: str, b_words: str) -> str:
    return f"Maine theek se nahi suna. Aapne {a_words} kaha ya {b_words}?"


def success_line(words_form: str, name: str) -> str:
    return f"Ho gaya. {words_form} {name} ko bhej diye. SMS aa raha hai."


def ledger_hit_line(name: str) -> str:
    return f"{name}, jaise pichli baar."


def payee_enumerate_line(names: list[str]) -> str:
    if len(names) == 1:
        return f"Aapka ek hi payee hai, {names[0]}. Sahi hai?"
    *head, last = names
    listed = ", ".join(head) + f", ya {last}"
    return f"Aapke {len(names)} payees hain. {listed}?"
