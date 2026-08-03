"""pytest 共享 fixtures。"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings

from rag_cs.config import Settings, get_settings
from rag_cs.kb.registry import KBMetaStore
from rag_cs.vectorstore import store as store_mod
from rag_cs.vectorstore.store import VectorStoreService


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """把数据目录指到临时路径，避免测试污染真实 data/。

    同时清掉 get_settings 的 lru_cache，确保下一次读取拿到新的环境变量。
    """
    get_settings.cache_clear()
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("KB_META_PATH", str(tmp_path / "kb_meta.json"))
    yield tmp_path
    get_settings.cache_clear()


class FakeEmbeddings(Embeddings):
    """确定性假 embedding：按字符 ord 取模分桶到 8 维，相似文本向量接近。"""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    @staticmethod
    def _vec(text: str) -> list[float]:
        vec = [0.0] * 8
        for ch in text:
            vec[ord(ch) % 8] += 1.0
        return vec


def _fake_get_embeddings(_settings: Settings | None = None) -> Embeddings:
    return FakeEmbeddings()


@pytest.fixture
def vstore(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> VectorStoreService:
    """用假 embedding 构造 VectorStoreService，数据落 tmp_data_dir。"""
    monkeypatch.setattr(store_mod, "get_embeddings", _fake_get_embeddings)
    return VectorStoreService()


@pytest.fixture
def registry(tmp_data_dir: Path) -> KBMetaStore:
    """KBMetaStore，元数据落 tmp_data_dir。"""
    return KBMetaStore()
