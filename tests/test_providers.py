"""providers 工厂分发逻辑测试（不联网，mock 掉真实构造）。"""

from typing import Any

import pytest

from rag_cs.config import ChatProvider, EmbeddingProvider, Settings
from rag_cs.providers import factory


def test_chat_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake(name: str) -> Any:
        def _chat(s: Settings) -> str:
            seen.append(name)
            return name

        return _chat

    monkeypatch.setattr(factory.openai_provider, "get_chat_model", fake("openai"))
    monkeypatch.setattr(factory.ollama_provider, "get_chat_model", fake("ollama"))
    monkeypatch.setattr(factory.xinference_provider, "get_chat_model", fake("xinference"))

    s = Settings(chat_provider=ChatProvider.OLLAMA)
    assert factory.get_chat_model(s) == "ollama"
    assert seen == ["ollama"]


def test_embedding_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake(name: str) -> Any:
        def _emb(s: Settings) -> str:
            seen.append(name)
            return name

        return _emb

    monkeypatch.setattr(factory.openai_provider, "get_embeddings", fake("openai"))
    monkeypatch.setattr(factory.ollama_provider, "get_embeddings", fake("ollama"))
    monkeypatch.setattr(factory.xinference_provider, "get_embeddings", fake("xinference"))

    s = Settings(embedding_provider=EmbeddingProvider.XINFERENCE)
    assert factory.get_embeddings(s) == "xinference"
    assert seen == ["xinference"]
