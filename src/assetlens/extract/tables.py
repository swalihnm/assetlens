"""Generic HTML-table helpers: label + numeric cells, with raw text kept for provenance."""
from __future__ import annotations

import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
NUM = re.compile(r"^\(?-?\$?\s*[\d,]+(\.\d+)?\)?$")
DASHES = ("—", "–", "�", "-")


def soup(html: bytes | str) -> BeautifulSoup:
    return BeautifulSoup(html if isinstance(html, str) else html.decode("utf8", "ignore"), "lxml")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def to_num(tok: str) -> float | None:
    t = tok.replace("$", "").replace(",", "").replace(" ", "")
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def rows(tbl) -> list[tuple[str, list[float | None], str]]:
    """(label, numbers, raw_row_text). Dash cells count as 0; $ / % / ) spacer cells skipped."""
    out = []
    for tr in tbl.find_all("tr"):
        cells = [norm(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c]
        if not cells:
            continue
        label, nums, i = cells[0], [], 1
        while i < len(cells):
            c = cells[i]
            if c in ("$", "%", ")"):
                i += 1
                continue
            if c.startswith("(") and not c.endswith(")") and i + 1 < len(cells) and cells[i + 1] == ")":
                c += ")"
            if c in DASHES:
                nums.append(0.0)
            elif NUM.match(c):
                nums.append(to_num(c))
            i += 1
        out.append((label, nums, " | ".join(cells)))
    return out


def find_tables(sp, *anchors: str):
    for i, t in enumerate(sp.find_all("table")):
        x = norm(t.get_text(" "))
        if all(a in x for a in anchors):
            yield i, t
