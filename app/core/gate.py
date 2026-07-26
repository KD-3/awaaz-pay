"""The confidence gate on the amount slot, and its fallback (§8.4).

Primary path uses a Saaras v3 confidence score if the streaming API exposes
one. Whether it does is an open question in IDEA_SCOPE.md (§1, §8.4) - this
module implements both paths and prefers the primary one only when a
confidence value is actually supplied, so the fallback silently becomes the
one that runs until that's confirmed against a live stream.
"""
from __future__ import annotations

from dataclasses import dataclass

PLAUSIBILITY_MIN_PAISE = 100 * 100
PLAUSIBILITY_MAX_PAISE = 50_000 * 100


@dataclass
class GateResult:
    passed: bool
    reason: str
    candidates: tuple[int, int] | None = None  # (heard, round-neighbour), in paise


def plausibility_band_ok(amount_paise: int) -> bool:
    return PLAUSIBILITY_MIN_PAISE <= amount_paise <= PLAUSIBILITY_MAX_PAISE


def round_number_neighbor(amount_paise: int) -> int:
    """Remittances are overwhelmingly round. Round to the nearest power-of-ten
    step implied by the amount's own magnitude (e.g. 4,973 -> 5,000)."""
    rupees = amount_paise // 100
    if rupees == 0:
        return amount_paise
    magnitude = 10 ** (len(str(rupees)) - 1)
    rounded = round(rupees / magnitude) * magnitude
    return rounded * 100


def gate_amount(
    amount_paise: int,
    confidence: float | None = None,
    confidence_threshold: float = 0.75,
    second_parse_paise: int | None = None,
) -> GateResult:
    if confidence is not None:
        passed = confidence >= confidence_threshold
        reason = "confidence"
    else:
        band_ok = plausibility_band_ok(amount_paise)
        parses_agree = second_parse_paise is None or second_parse_paise == amount_paise
        is_round = round_number_neighbor(amount_paise) == amount_paise
        passed = band_ok and parses_agree and is_round
        reason = "fallback"

    if passed:
        return GateResult(passed=True, reason=reason)

    neighbor = round_number_neighbor(amount_paise)
    candidates = (amount_paise, neighbor) if neighbor != amount_paise else (amount_paise, amount_paise)
    return GateResult(passed=False, reason=reason, candidates=candidates)
