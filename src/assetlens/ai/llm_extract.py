"""M17 / M2 fallback - LLM-assisted table extraction into a strict Pydantic schema, with source-cell grounding,
roll-forward closure checks and a human review queue. Unreviewed values never reach the marts."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field, ValidationError, model_validator

from assetlens.ai.gateway import Gateway
from assetlens.extract.tables import norm, rows

ROOT = Path(__file__).resolve().parents[3]
QUEUE = ROOT / "data" / "interim" / "review_queue.csv"
SYSTEM = ("Extract the assets-under-management roll-forward for the TOTAL company/segment, current quarter only. Return JSON with keys: "
          "begin, net_flows, market, other, end (numbers exactly as printed, in the table's units), unit ('billions' or 'millions'), "
          "source_rows (the exact row labels you used). Use 0 for 'other' if none. Do not compute or estimate values.")


class RollForward(BaseModel):
    begin: float
    net_flows: float
    market: float
    other: float = 0.0
    end: float
    unit: str = Field(pattern="^(billions|millions)$")
    source_rows: list[str] = Field(min_length=2)

    @model_validator(mode="after")
    def closes(self):
        tol = max(0.35 if self.unit == "billions" else 1.5, 0.0005 * abs(self.end))
        if abs(self.begin + self.net_flows + self.market + self.other - self.end) > tol:
            raise ValueError("roll-forward does not close")
        return self


def table_text(tbl) -> str:
    return "\n".join(raw for _, _, raw in rows(tbl))


def grounded(rf: RollForward, text: str) -> list[str]:
    """Every extracted number must appear in the source text (guards against hallucinated values)."""
    flat = text.replace(",", "").replace("(", "-").replace(")", "")
    missing = []
    for name in ("begin", "net_flows", "market", "end"):
        v = getattr(rf, name)
        forms = {f"{abs(v):g}", f"{abs(v):.1f}", f"{abs(v):.0f}", f"{abs(v):.2f}"}
        if not any(f in flat for f in forms):
            missing.append(f"{name}={v}")
    return missing


def extract(gw: Gateway, tbl, meta: dict) -> dict:
    text = table_text(tbl)
    status, reason, rf = "pending_review", "", None
    try:
        data = gw.json(SYSTEM, text)
        rf = RollForward(**data)
        miss = grounded(rf, text)
        if miss:
            status, reason = "rejected", "ungrounded numbers: " + ", ".join(miss)
        else:
            missing_rows = [r for r in rf.source_rows if norm(r) not in norm(text)]
            if missing_rows:
                status, reason = "rejected", f"source rows not in table: {missing_rows}"
    except (ValidationError, json.JSONDecodeError, ValueError, KeyError) as e:
        status, reason = "rejected", f"schema/closure: {str(e)[:120]}"
    rec = dict(**meta, status=status, reason=reason, reviewed=False, extracted=json.dumps(rf.model_dump()) if rf else "", source_text=text[:1500])
    return rec


def enqueue(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(QUEUE, index=False)
    return df


def approved(path: Path = QUEUE) -> pd.DataFrame:
    """Only rows a human has marked reviewed AND approved are released to the marts."""
    d = pd.read_csv(path)
    return d[(d.status == "pending_review") & (d.get("decision", "") == "approve") & d.reviewed.astype(bool)] if "decision" in d else d.iloc[0:0]
