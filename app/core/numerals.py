"""Deterministic Hindi/Hinglish amount parsing and speech formatting (§10).

Never delegate this to the LLM or to TTS preprocessing - both are unreliable
at lakh/crore grouping and neither is debuggable live on stage.
"""
import re

# Hindi number words 1-99, Latin transliteration. Index = value.
_ONES = [
    "zero", "ek", "do", "teen", "chaar", "paanch", "chhah", "saat", "aath", "nau",
    "das", "gyarah", "baarah", "terah", "chaudah", "pandrah", "solah", "satrah", "atharah", "unnis",
    "bees", "ikkis", "baais", "teis", "chaubis", "pachchis", "chhabbis", "sattais", "athais", "unatis",
    "tees", "ikattis", "battis", "tetis", "chauntis", "paintis", "chhattis", "saintis", "adhtis", "untalis",
    "chalis", "iktalis", "biyalis", "tetalis", "chavalis", "paintalis", "chhiyalis", "saintalis", "adtalis", "uncchas",
    "pachaas", "ikyavan", "bavan", "tirpan", "chauvan", "pachpan", "chhappan", "sattavan", "atthavan", "unsath",
    "saath", "iksath", "baasath", "tirsath", "chausath", "painsath", "chhiyasath", "sadsath", "adsath", "unhattar",
    "sattar", "ikhattar", "bahattar", "tihattar", "chauhattar", "pachhattar", "chhihattar", "sathattar", "athhattar", "unnasi",
    "assi", "ikyasi", "bayasi", "tirasi", "chaurasi", "pachasi", "chhiyasi", "sathasi", "atthasi", "navasi",
    "nabbe", "ikyanave", "banave", "tiranave", "chauranave", "pachanave", "chhiyanave", "sattanave", "atthanave", "ninyanave",
]

# Alternate spellings accepted when parsing (canonical spelling above is used for output).
_ALIASES = {
    "char": 4, "chaar": 4,
    "panch": 5, "paanch": 5,
    "che": 6, "chhe": 6, "chhah": 6,
    "bis": 20, "bees": 20,
    # English number words - defensive: slot extraction is instructed to
    # preserve the amount phrase verbatim, but an LLM or a caller may still
    # produce English words instead of Hindi ones.
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}

_WORD_VALUES = {word: value for value, word in enumerate(_ONES)}
_WORD_VALUES.update(_ALIASES)

_MULTIPLIERS = {
    "sau": 100,
    "hundred": 100,
    "hazaar": 1000,
    "hazar": 1000,
    "thousand": 1000,
    "k": 1000,
    "lakh": 1000_00,
    "lac": 1000_00,
    "crore": 1_00_00_000,
}

_TOKEN_RE = re.compile(r"\d+|[a-z]+")


def _ones_word(n: int) -> str:
    if 0 <= n <= 99:
        return _ONES[n]
    return str(n)


def parse_spoken_amount(text: str, lang: str = "hi") -> int:
    """Parse a spoken Hindi/Hinglish/English amount phrase into paise (int)."""
    tokens = _TOKEN_RE.findall(text.lower())
    total = 0
    current = 0
    for tok in tokens:
        if tok.isdigit():
            current += int(tok)
        elif tok in _WORD_VALUES:
            current += _WORD_VALUES[tok]
        elif tok in _MULTIPLIERS:
            mult = _MULTIPLIERS[tok]
            if current == 0:
                current = 1
            total += current * mult
            current = 0
        # unknown tokens (rupaye, rupees, ka, aur, ...) are ignored
    total += current
    return total * 100


def _indian_group_words(rupees: int) -> list[str]:
    if rupees == 0:
        return ["zero"]
    crore, rem = divmod(rupees, 1_00_00_000)
    lakh, rem = divmod(rem, 1000_00)
    thousand, rem = divmod(rem, 1000)
    hundred, rem = divmod(rem, 100)

    parts: list[str] = []
    if crore:
        parts.append(f"{_ones_word(crore)} crore")
    if lakh:
        parts.append(f"{_ones_word(lakh)} lakh")
    if thousand:
        parts.append(f"{_ones_word(thousand)} hazaar")
    if hundred:
        parts.append("sau" if hundred == 1 else f"{_ones_word(hundred)} sau")
    if rem:
        parts.append(_ones_word(rem))
    return parts


_DIGIT_WORDS = ["zero", "ek", "do", "teen", "chaar", "paanch", "chhah", "saat", "aath", "nau"]


def format_amount_for_speech(paise: int, lang: str = "hi") -> tuple[str, str]:
    """Return (words_form, digits_form) for the amount, both meant to be read aloud together."""
    rupees = paise // 100
    words_form = " ".join(_indian_group_words(rupees)) + " rupaye"
    digits_form = ", ".join(_DIGIT_WORDS[int(d)] for d in str(rupees))
    return words_form, digits_form
