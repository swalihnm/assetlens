"""Live text-to-SQL evaluation through the gateway (default: Ollama cloud, free-tier model)."""
from __future__ import annotations

import json
import sys

from assetlens.ai import text2sql as T
from assetlens.ai.eval_set import items
from assetlens.ai.gateway import Gateway


def run(provider: str = "ollama", model: str = "gemma4:31b-cloud") -> dict:
    gw = Gateway(provider, model=model, log=True)
    its = items()
    out = {"model": model, "provider": provider, "by_category": {}}
    res = T.execution_accuracy(its, T.LLMGenerator(gw))
    out.update({k: v for k, v in res.items() if k != "failures"})
    for cat in sorted({i.category for i in its}):
        sub = [i for i in its if i.category == cat]
        r = T.execution_accuracy(sub, T.LLMGenerator(gw))
        out["by_category"][cat] = f"{r['correct']}/{r['n']}"
    out["calls"] = len(gw.calls)
    out["mean_latency_s"] = sum(c.latency_s for c in gw.calls) / max(1, len(gw.calls))
    out["failures_sample"] = [(f[0], f[2]) for f in res["failures"][:8]]
    return out


if __name__ == "__main__":
    print(json.dumps(run(*sys.argv[1:3]), indent=1, default=str))
