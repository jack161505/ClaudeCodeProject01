"""providers 测试：工厂分发（mock）+ 真实构造（ollama/xinference/openai，离线）。"""

from typing import Any

import pytest
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from rag_cs.config import ChatProvider, EmbeddingProvider, Settings
from rag_cs.providers import factory, ollama_provider, openai_provider, xinference_provider


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

    s = Settings(chat_provider=ChatProvider.OLLAMA, _env_file=None)
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

    s = Settings(embedding_provider=EmbeddingProvider.XINFERENCE, _env_file=None)
    assert factory.get_embeddings(s) == "xinference"
    assert seen == ["xinference"]


def test_ollama_provider_constructs_without_key() -> None:
    s = Settings(
        chat_provider=ChatProvider.OLLAMA,
        chat_model="llama3",
        embedding_provider=EmbeddingProvider.OLLAMA,
        embedding_model="nomic-embed-text",
        _env_file=None,
    )

    assert isinstance(ollama_provider.get_chat_model(s), ChatOllama)
    assert isinstance(ollama_provider.get_embeddings(s), OllamaEmbeddings)


def test_xinference_provider_constructs_with_dummy_key() -> None:
    s = Settings(
        chat_provider=ChatProvider.XINFERENCE,
        chat_model="qwen",
        embedding_provider=EmbeddingProvider.XINFERENCE,
        embedding_model="bge-m3",
        _env_file=None,
    )

    assert isinstance(xinference_provider.get_chat_model(s), ChatOpenAI)
    assert isinstance(xinference_provider.get_embeddings(s), OpenAIEmbeddings)


def test_openai_provider_constructs_with_key() -> None:
    s = Settings(
        openai_api_key="sk-fake",
        chat_model="gpt-4o-mini",
        embedding_model="text-embedding-3-small",
        _env_file=None,
    )

    assert isinstance(openai_provider.get_chat_model(s), ChatOpenAI)
    assert isinstance(openai_provider.get_embeddings(s), OpenAIEmbeddings)


def test_factory_returns_ollama_model() -> None:
    s = Settings(chat_provider=ChatProvider.OLLAMA, chat_model="llama3", _env_file=None)
    assert isinstance(factory.get_chat_model(s), ChatOllama)
