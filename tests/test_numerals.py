from app.core.numerals import format_amount_for_speech, parse_spoken_amount


def test_format_5000():
    words, digits = format_amount_for_speech(5000 * 100)
    assert words == "paanch hazaar rupaye"
    assert digits == "paanch, zero, zero, zero"


def test_format_452318():
    words, digits = format_amount_for_speech(452318 * 100)
    assert words == "chaar lakh bavan hazaar teen sau atharah rupaye"
    assert digits == "chaar, paanch, do, teen, ek, aath"


def test_format_100():
    words, digits = format_amount_for_speech(100 * 100)
    assert words == "sau rupaye"
    assert digits == "ek, zero, zero"


def test_format_1250000():
    words, digits = format_amount_for_speech(1250000 * 100)
    assert words == "baarah lakh pachaas hazaar rupaye"


def test_parse_paanch_hazaar():
    assert parse_spoken_amount("paanch hazaar") == 500000


def test_parse_5_thousand():
    assert parse_spoken_amount("5 thousand") == 500000


def test_parse_5k():
    assert parse_spoken_amount("5k") == 500000


def test_parse_paanch_hazaar_paanch_sau():
    assert parse_spoken_amount("paanch hazaar paanch sau") == 550000


def test_parse_with_filler_words():
    assert parse_spoken_amount("Sunita ko paanch hazaar rupaye bhejo") == 500000
