from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SiteConfig:
    id: str
    domain: str
    priority: int
    enabled: bool


@dataclass(frozen=True)
class SearchConfig:
    provider: str
    top_k_per_site: int
    max_total_sources: int
    query_template: str


@dataclass(frozen=True)
class FetchConfig:
    timeout_seconds: int
    max_content_chars: int
    user_agent: str


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    max_tokens_intake: int
    max_tokens_source_reader: int
    max_tokens_synthesizer: int
    model_preference: list[str]


@dataclass(frozen=True)
class TrialsConfig:
    max_readers: int
    max_search_results: int
    rank_recruiting_boost: int


@dataclass(frozen=True)
class SourceRegistry:
    sites: list[SiteConfig]
    search: SearchConfig
    fetch: FetchConfig
    llm: LLMConfig
    trials: TrialsConfig

    @property
    def enabled_sites(self) -> list[SiteConfig]:
        return sorted([s for s in self.sites if s.enabled], key=lambda s: s.priority)


def load_registry(yaml_path: Path) -> SourceRegistry:
    raw = yaml.safe_load(yaml_path.read_text())
    sites = [SiteConfig(**s) for s in raw["sites"]]
    search = SearchConfig(**raw["search"])
    fetch = FetchConfig(**raw["fetch"])
    llm = LLMConfig(**raw["llm"])
    trials_raw = raw.get("trials", {})
    trials = TrialsConfig(
        max_readers=trials_raw.get("max_readers", 5),
        max_search_results=trials_raw.get("max_search_results", 10),
        rank_recruiting_boost=trials_raw.get("rank_recruiting_boost", 2),
    )
    return SourceRegistry(sites=sites, search=search, fetch=fetch, llm=llm, trials=trials)
