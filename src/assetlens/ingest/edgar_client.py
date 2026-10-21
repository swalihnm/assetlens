"""Rate-limited, disk-cached SEC EDGAR client (fair-access compliant)."""
from __future__ import annotations

import hashlib
import os
import threading
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()
RAW = Path(__file__).resolve().parents[3] / "data" / "raw"
MAX_RPS = 8  # below SEC's 10 req/s ceiling


class EdgarClient:
    def __init__(self, cache_dir: Path = RAW, max_rps: float = MAX_RPS):
        ua = os.environ.get("SEC_USER_AGENT")
        if not ua:
            raise RuntimeError("Set SEC_USER_AGENT (e.g. 'Name email@example.com')")
        self.http = httpx.Client(headers={"User-Agent": ua}, timeout=60, follow_redirects=True)
        self.cache = cache_dir
        self.min_gap = 1.0 / max_rps
        self._last = 0.0
        self._lock = threading.Lock()
        self.network_calls = 0

    def _path(self, url: str) -> Path:
        tail = url.split("/")[-1][:60] or "index"
        return self.cache / "sec" / (hashlib.sha1(url.encode()).hexdigest()[:16] + "_" + tail)

    def _throttle(self) -> None:
        with self._lock:
            wait = self.min_gap - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(min=1, max=30))
    def _fetch(self, url: str) -> bytes:
        self._throttle()
        self.network_calls += 1
        r = self.http.get(url)
        r.raise_for_status()
        return r.content

    def get(self, url: str) -> bytes:
        p = self._path(url)
        if p.exists():
            return p.read_bytes()
        data = self._fetch(url)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return data

    def get_json(self, url: str):
        import json
        return json.loads(self.get(url))
