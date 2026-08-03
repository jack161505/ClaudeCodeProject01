"""IngestionPipeline 测试：用假 embedding 离线验证切分入库、重新入库与元数据。

FakeEmbeddings / vstore / registry fixture 见 conftest.py。
"""

import pytest

from rag_cs.config import Settings
from rag_cs.ingestion.pipeline import IngestionPipeline
from rag_cs.kb.registry import KBMetaStore, KnowledgeBaseNotFound
from rag_cs.vectorstore.store import VectorStoreService


@pytest.fixture
def pipeline(vstore: VectorStoreService, registry: KBMetaStore) -> IngestionPipeline:
    """用假 embedding 的 vstore + 临时 registry 构造流水线。"""
    return IngestionPipeline(vstore=vstore, registry=registry)


def test_ingest_stores_and_registers(
    pipeline: IngestionPipeline,
    registry: KBMetaStore,
    vstore: VectorStoreService,
) -> None:
    kb = registry.create("客服手册", "常见问题")

    n = pipeline.ingest(
        kb.id,
        "faq.md",
        "# 密码\n如何重置密码？步骤如下。\n\n# 退款\n退款流程说明。",
    )

    assert n >= 1
    refreshed = registry.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 1
    assert refreshed.chunk_count == n

    hits = vstore.search([kb.collection_name], "密码重置", top_k=4)
    assert hits
    assert all(h.metadata["source"] == "faq.md" for h in hits)
    assert all(h.metadata["kb_id"] == kb.id for h in hits)


def test_ingest_empty_returns_zero(
    pipeline: IngestionPipeline,
    registry: KBMetaStore,
) -> None:
    kb = registry.create("空手册")

    n = pipeline.ingest(kb.id, "empty.md", "   \n\n   ")

    assert n == 0
    refreshed = registry.get(kb.id)
    assert refreshed is not None
    assert refreshed.chunk_count == 0


def test_ingest_splits_long_doc(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    # 小 chunk_size 强制多块
    s = Settings(chunk_size=50, chunk_overlap=10)
    pipe = IngestionPipeline(vstore=vstore, registry=registry, settings=s)
    kb = registry.create("长手册")

    long_text = "密码重置的详细步骤说明。" * 20  # > 50 字符

    n = pipe.ingest(kb.id, "long.md", long_text)

    assert n > 1
    refreshed = registry.get(kb.id)
    assert refreshed is not None
    assert refreshed.chunk_count == n


def test_reingest_replaces_chunks(
    pipeline: IngestionPipeline,
    registry: KBMetaStore,
    vstore: VectorStoreService,
) -> None:
    kb = registry.create("手册")
    pipeline.ingest(kb.id, "a.md", "苹果苹果苹果")
    pipeline.ingest(kb.id, "b.md", "香蕉香蕉香蕉")
    # 重新入库 a.md，内容换成葡萄
    pipeline.ingest(kb.id, "a.md", "葡萄葡萄葡萄")

    hits = vstore.search([kb.collection_name], "果", top_k=10)
    contents = " ".join(h.content for h in hits)
    assert "苹果" not in contents  # 旧 chunk 已被替换
    assert "葡萄" in contents
    assert "香蕉" in contents

    refreshed = registry.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 2  # 仍是两份文档
    a_doc = next(d for d in refreshed.documents if d.source == "a.md")
    assert a_doc.chunk_count >= 1


def test_ingest_missing_kb_raises(pipeline: IngestionPipeline) -> None:
    with pytest.raises(KnowledgeBaseNotFound):
        pipeline.ingest("nope", "x.md", "内容")
