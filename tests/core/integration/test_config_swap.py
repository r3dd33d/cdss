"""SC-005: toggling config changes behavior without code edits."""
import pytest
import yaml
from pathlib import Path

from cdss.sources.registry import load_registry


def test_toggle_site_enabled(tmp_path):
    cfg = {
        "sites": [
            {"id": "nccn", "domain": "nccn.org", "priority": 1, "enabled": True},
            {"id": "esmo", "domain": "esmo.org", "priority": 1, "enabled": False},
        ],
        "search": {"provider": "serper", "top_k_per_site": 1, "max_total_sources": 5,
                   "query_template": "{condition} {stage}"},
        "fetch": {"timeout_seconds": 15, "max_content_chars": 1000, "user_agent": "test"},
        "llm": {"provider": "groq", "max_tokens_intake": 512, "max_tokens_source_reader": 512,
                "max_tokens_synthesizer": 1024, "model_preference": ["llama3-8b-8192"]},
    }
    p = tmp_path / "sources.yaml"
    p.write_text(yaml.dump(cfg))
    reg = load_registry(p)
    enabled_domains = [s.domain for s in reg.enabled_sites]
    assert "nccn.org" in enabled_domains
    assert "esmo.org" not in enabled_domains

    # Toggle esmo on — no code change required.
    cfg["sites"][1]["enabled"] = True
    p.write_text(yaml.dump(cfg))
    reg2 = load_registry(p)
    assert "esmo.org" in [s.domain for s in reg2.enabled_sites]


def test_model_preference_order(tmp_path):
    cfg_path = Path(__file__).parent.parent.parent.parent / "cdss/config/sources.yaml"
    reg = load_registry(cfg_path)
    # First preference should be deepseek; order is preserved from YAML.
    assert reg.llm.model_preference[0] == "deepseek-r1-distill-llama-70b"
