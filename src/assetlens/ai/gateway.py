"""M17 - provider-agnostic LLM gateway (Claude / OpenAI / Ollama / offline mock) with cost and latency logging.

Live providers need credentials (ANTHROPIC_API_KEY / OPENAI_API_KEY) or a local Ollama server; the `mock` provider
is deterministic and lets every pipeline be tested offline. Calls are logged to DuckDB table `llm_calls`.
"""
from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import duckdb
import httpx

from assetlens.warehouse.build import DB

# USD per million tokens (input, output) - placeholders for cost logging; update from provider pricing pages
PRICES = {"anthropic": (3.0, 15.0), "openai": (2.5, 10.0), "ollama": (0.0, 0.0), "mock": (0.0, 0.0)}


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    latency_s: float
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class Gateway:
    provider: str = "mock"
    model: str = ""
    mock_fn: Callable[[str, str], str] | None = None
    log: bool = True
    calls: list[LLMResult] = field(default_factory=list)

    def complete(self, system: str, prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> LLMResult:
        t0 = time.perf_counter()
        if self.provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic()
            r = client.messages.create(model=self.model or "claude-sonnet-5-5", max_tokens=max_tokens, temperature=temperature,
                                       system=system, messages=[{"role": "user", "content": prompt}])
            text, tin, tout = r.content[0].text, r.usage.input_tokens, r.usage.output_tokens
        elif self.provider == "openai":
            r = httpx.post("https://api.openai.com/v1/chat/completions", timeout=120,
                           headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                           json={"model": self.model or "gpt-4o-mini", "temperature": temperature, "max_tokens": max_tokens,
                                 "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}).json()
            text, tin, tout = r["choices"][0]["message"]["content"], r["usage"]["prompt_tokens"], r["usage"]["completion_tokens"]
        elif self.provider == "ollama":
            r = httpx.post(os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/chat", timeout=300,
                           json={"model": self.model or "llama3.1", "stream": False, "options": {"temperature": temperature},
                                 "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}).json()
            text, tin, tout = r["message"]["content"], r.get("prompt_eval_count", 0), r.get("eval_count", 0)
        elif self.provider == "mock":
            text = self.mock_fn(system, prompt) if self.mock_fn else "{}"
            tin, tout = len((system + prompt).split()), len(text.split())
        else:
            raise ValueError(f"unknown provider {self.provider}")
        pin, pout = PRICES[self.provider]
        res = LLMResult(text, self.provider, self.model or self.provider, time.perf_counter() - t0, tin, tout, (tin * pin + tout * pout) / 1e6)
        self.calls.append(res)
        if self.log:
            self._log(res)
        return res

    @staticmethod
    def _log(r: LLMResult) -> None:
        try:
            con = duckdb.connect(str(DB))
            con.execute("create table if not exists llm_calls (ts timestamp, provider varchar, model varchar, latency_s double, "
                        "input_tokens bigint, output_tokens bigint, cost_usd double)")
            con.execute("insert into llm_calls values (now(), ?, ?, ?, ?, ?, ?)",
                        [r.provider, r.model, r.latency_s, r.input_tokens, r.output_tokens, r.cost_usd])
            con.close()
        except Exception:      # logging must never break a call (e.g. DB locked by another reader)
            pass

    def json(self, system: str, prompt: str, **kw) -> dict:
        txt = self.complete(system, prompt, **kw).text.strip()
        if txt.startswith("```"):
            txt = txt.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(txt)
