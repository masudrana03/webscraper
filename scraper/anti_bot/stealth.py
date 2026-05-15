"""Anti-bot utilities: stealth headers, proxy rotation, fingerprint spoofing."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field


@dataclass
class ProxyRotator:
    """Rotate through a list of proxies."""

    proxies: list[str] = field(default_factory=list)
    _current_index: int = 0
    _fail_counts: dict[str, int] = field(default_factory=dict)
    max_failures: int = 3

    def add(self, proxy: str):
        if proxy not in self.proxies:
            self.proxies.append(proxy)

    def add_many(self, proxy_list: list[str]):
        for p in proxy_list:
            self.add(p)

    def load_from_file(self, filepath: str):
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    self.add(line)

    def next(self) -> str | None:
        if not self.proxies:
            return None

        # Skip failed proxies
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self._current_index]
            self._current_index = (self._current_index + 1) % len(self.proxies)

            if self._fail_counts.get(proxy, 0) < self.max_failures:
                return proxy
            attempts += 1

        return None  # All proxies exhausted

    def report_success(self, proxy: str):
        self._fail_counts[proxy] = 0

    def report_failure(self, proxy: str):
        self._fail_counts[proxy] = self._fail_counts.get(proxy, 0) + 1

    @property
    def count(self) -> int:
        return len(self.proxies)


def stealth_headers() -> dict[str, str]:
    """Generate realistic browser headers with randomized order."""
    from fake_useragent import UserAgent

    ua = UserAgent()
    base = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    return base


def human_delay(min_s: float = 1.0, max_s: float = 3.0):
    """Sleep a random duration to mimic human behavior."""
    time.sleep(random.uniform(min_s, max_s))


class RateLimiter:
    """Simple rate limiter for requests."""

    def __init__(self, requests_per_second: float = 2.0):
        self.min_interval = 1.0 / requests_per_second
        self._last_request = 0.0

    def wait(self):
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()
