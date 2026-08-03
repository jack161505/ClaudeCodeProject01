"""config 测试：默认值、环境变量加载、lru_cache、枚举。"""

import pytest

from rag_cs.config import (
    ChatProvider,
    EmbeddingProvider,
    Settings,
    get_settings,
)


def test_default_settings() -> None:
    s = Settings(_env_file=None)

    assert s.chat_provider is ChatProvider.OPENAI
    assert s.chat_model == "gpt-4o-mini"
    assert s.embedding_provider is EmbeddingProvider.OPENAI
    assert s.embedding_model == "text-embedding-3-small"
    assert s.chunk_size == 500
    assert s.chunk_overlap == 50
    assert s.retrieval_top_k == 4
    assert s.openai_api_key is None
    assert s.chroma_dir == "data/chroma"
    assert s.kb_meta_path == "data/kb_meta.json"


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAT_PROVIDER", "ollama")
    monkeypatch.setenv("CHAT_MODEL", "llama3")
    monkeypatch.setenv("CHUNK_SIZE", "200")
    monkeypatch.setenv("RETRIEVAL_TOP_K", "8")

    s = Settings(_env_file=None)

    assert s.chat_provider is ChatProvider.OLLAMA
    assert s.chat_model == "llama3"
    assert s.chunk_size == 200
    assert s.retrieval_top_k == 8


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b

    get_settings.cache_clear()
    c = get_settings()
    assert c is not a


def test_provider_enum_is_str() -> None:
    assert ChatProvider.OPENAI == "openai"
    assert ChatProvider.OLLAMA == "ollama"
    assert ChatProvider.XINFERENCE == "xinference"
    assert EmbeddingProvider.OPENAI == "openai"
