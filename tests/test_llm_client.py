"""Tests for provider resolution in core.llm_client."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


fake_langchain = types.ModuleType("langchain_openai")


class _FakeChatOpenAI:
    def __init__(self, *args, **kwargs):  # pragma: no cover - stub
        pass


fake_langchain.ChatOpenAI = _FakeChatOpenAI
sys.modules.setdefault("langchain_openai", fake_langchain)


def test_coe_provider_reuses_default_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from core import llm_client as llm_client_module

    llm_client = importlib.reload(llm_client_module)

    default_model = llm_client.model_registry.get_default_model()
    assert default_model is not None

    default_client = llm_client.get_client_for_model(default_model.model_id)

    model_id = "coe-agent-test"
    llm_client.model_registry.register_model(
        model_id=model_id,
        name="CoE Agent Test",
        description="Fallback alias for CoE orchestration tests.",
        provider="CoE",
        provider_model_id=default_model.model_id,
    )

    coe_client = llm_client.get_client_for_model(model_id)

    assert coe_client is default_client
    assert (
        llm_client.resolve_effective_model_id(model_id)
        == default_model.model_id
    )
