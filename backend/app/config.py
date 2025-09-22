from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    http_timeout: float = Field(default=8.0)
    resolver_concurrency: int = Field(default=100)
    probe_concurrency: int = Field(default=20)
    bruteforce_words: List[str] = Field(default_factory=lambda: ["www", "api", "dev", "mail", "staging", "test"])
    bruteforce_extra_wordlist: Optional[str] = Field(default=None)
    seclists_wordlist: Optional[str] = Field(default=None)
    seclists_min_words: int = Field(default=500)
    massdns_bin: Optional[str] = Field(default=None)
    massdns_resolvers_file: str = Field(default="app/resolvers.txt")
    massdns_batch_size: int = Field(default=400)
    crtsh_timeout: float = Field(default=20.0)
    crtsh_user_agent: str = Field(default="oss-subfinder/1.0")
    enable_history: bool = Field(default=True)
    postgres_dsn: Optional[str] = Field(default=None)
    recent_scans_limit: int = Field(default=50)
    per_domain_history_limit: int = Field(default=10)
    rate_limit_requests: int = Field(default=60)
    rate_limit_window: float = Field(default=60.0)
    trust_x_forwarded_for: bool = Field(default=False)

    def massdns_path(self) -> Optional[str]:
        candidates = []
        if self.massdns_bin:
            candidates.append(self.massdns_bin)
        candidates.extend(
            [
                "/opt/massdns/massdns",
                shutil.which("massdns"),
            ]
        )
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.is_file():
                return str(path)
        return None

    def resolvers_path(self) -> str:
        configured = Path(self.massdns_resolvers_file)
        if configured.is_file():
            return str(configured)
        fallback = Path(__file__).resolve().parent / "resolvers.txt"
        if fallback.is_file():
            return str(fallback)
        return str(configured)

    def extra_bruteforce_words(self) -> List[str]:
        words: List[str] = []
        for candidate in (self.bruteforce_extra_wordlist, self.seclists_wordlist):
            if not candidate:
                continue
            path = Path(candidate)
            if not path.is_file():
                continue
            try:
                with path.open("r", encoding="utf-8", errors="ignore") as handle:
                    for line in handle:
                        token = line.strip()
                        if not token:
                            continue
                        words.append(token)
                        if candidate == self.seclists_wordlist and self.seclists_min_words > 0:
                            if len(words) >= self.seclists_min_words:
                                break
            except OSError:
                continue
        return words


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
