"""M17 - numeric guardrail: every number in generated commentary must match a warehouse fact.

Matching rule: a number x written with d decimals matches a fact v if some unit variant of v (as-is, /1e3, /1e6, x100)
rounds to x at d decimals (so correct rounding passes, wrong figures do not). Years, quarter labels and ordinals are ignored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

NUM = re.compile(r"(?<![\w.])([-+−]?\$?\d[\d,]*(?:\.\d+)?)\s*(%|bps|bp|tn|bn|m|pp|x)?(?![\w])", re.I)
YEAR = re.compile(r"^(19|20)\d{2}$")


def extract_numbers(text: str) -> list[tuple[float, int, str, str]]:
    """(value, decimals, unit, raw) for each number in text; skips years and quarter tags."""
    out = []
    for m in NUM.finditer(text):
        raw = m.group(1)
        unit = (m.group(2) or "").lower()
        s = raw.replace(",", "").replace("$", "").replace("−", "-")
        if YEAR.match(s) and not unit and "$" not in raw:
            continue
        start = m.start()
        if start > 0 and text[start - 1] in "Qq" and re.fullmatch(r"[1-4]", s):
            continue
        if re.fullmatch(r"\d{1,2}", s) and text[m.end():m.end() + 2] in ("st", "nd", "rd", "th"):
            continue
        dec = len(s.split(".")[1]) if "." in s else 0
        out.append((float(s), dec, unit, raw))
    return out


def _variants(v: float) -> list[float]:
    return [v, v / 1e3, v / 1e6, v * 100, v * 1e4, abs(v), -v]


@dataclass
class GuardResult:
    ok: bool
    unmatched: list[str] = field(default_factory=list)
    checked: int = 0


def verify(text: str, facts: dict[str, float], extra_allowed: set[float] | None = None, single_use: bool = True) -> GuardResult:
    """Each fact may justify only ONE number in the text (single_use): a wrong figure that happens to equal a different
    fact elsewhere in the draft is then caught when that fact is needed again. Repeating a figure intentionally is flagged
    for review (conservative)."""
    allowed = extra_allowed or set()
    used: set[str] = set()
    bad, n = [], 0
    for x, dec, unit, raw in extract_numbers(text):
        n += 1
        if x in allowed:
            continue
        hit = None
        for key, v in facts.items():
            if single_use and key in used:
                continue
            if any(round(c, dec) == round(x, dec) or abs(abs(c) - abs(x)) <= 0.5 * 10 ** -dec + 1e-9 for c in _variants(float(v))):
                hit = key
                break
        if hit is None:
            bad.append(raw + (unit if unit else ""))
        else:
            used.add(hit)
    return GuardResult(ok=not bad, unmatched=bad, checked=n)


def perturb(text: str, seed: int = 0) -> tuple[str, str]:
    """Create a wrong-number draft: change one number by 8-60% (never rounding-level). Returns (draft, changed_raw)."""
    import random
    rnd = random.Random(seed)
    nums = [m for m in NUM.finditer(text) if not YEAR.match(m.group(1).replace(",", "")) and not (m.start() > 0 and text[m.start() - 1] in "Qq")]
    nums = [m for m in nums if not re.fullmatch(r"\d{1,2}", m.group(1)) or m.group(2)]
    m = rnd.choice(nums)
    s = m.group(1).replace(",", "").replace("$", "")
    v = float(s)
    dec = len(s.split(".")[1]) if "." in s else 0
    f = rnd.choice([0.6, 0.75, 0.9, 1.1, 1.25, 1.6])
    nv = round(v * f, dec) if round(v * f, dec) != round(v, dec) else round(v + 10 ** -dec * 5, dec)
    new = f"{nv:,.{dec}f}" if "," in m.group(1) else f"{nv:.{dec}f}"
    if "$" in m.group(1):
        new = "$" + new
    return text[:m.start(1)] + new + text[m.end(1):], m.group(1)
