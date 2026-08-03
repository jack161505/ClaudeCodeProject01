"""IngestionPipeline 测试：切分入库、元数据、隔离、重新入库与边界。

FakeEmbeddings / vstore / registry fixture 见 conftest.py。
"""

import pytest

from rag_cs.config import Settings
from rag_cs.ingestion.loader import load_markdown
from rag_cs.ingestion.pipeline import IngestionPipeline
from rag_cs.ingestion.splitter import split_document
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


def test_reingest_fewer_chunks(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    s = Settings(chunk_size=20, chunk_overlap=0)
    pipe = IngestionPipeline(vstore=vstore, registry=registry, settings=s)
    kb = registry.create("手册")

    pipe.ingest(kb.id, "doc.md", "一二三四五六七八九十" * 5)  # 多块
    first = registry.get(kb.id)
    assert first is not None and first.chunk_count > 1

    pipe.ingest(kb.id, "doc.md", "短")  # 重新入库，1 块

    refreshed = registry.get(kb.id)
    assert refreshed is not None
    assert refreshed.chunk_count == 1
    # 旧块已清除：搜索旧内容查不到
    hits = vstore.search([kb.collection_name], "十", top_k=5)
    assert all("十" not in h.content for h in hits)


def test_ingest_missing_kb_raises(pipeline: IngestionPipeline) -> None:
    with pytest.raises(KnowledgeBaseNotFound):
        pipeline.ingest("nope", "x.md", "内容")


def test_ingest_multiple_files(
    pipeline: IngestionPipeline,
    registry: KBMetaStore,
) -> None:
    kb = registry.create("手册")

    pipeline.ingest(kb.id, "a.md", "内容一")
    pipeline.ingest(kb.id, "b.md", "内容二")

    refreshed = registry.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 2


def test_ingest_multi_kb_isolation(
    pipeline: IngestionPipeline,
    registry: KBMetaStore,
    vstore: VectorStoreService,
) -> None:
    kb1 = registry.create("库一")
    kb2 = registry.create("库二")
    pipeline.ingest(kb1.id, "a.md", "独有内容苹果")

    # kb2 没有该内容
    assert vstore.search([kb2.collection_name], "苹果", top_k=3) == []
    # kb1 有
    hits = vstore.search([kb1.collection_name], "苹果", top_k=3)
    assert any("苹果" in h.content for h in hits)


def test_chunk_metadata_has_header(
    pipeline: IngestionPipeline,
    registry: KBMetaStore,
    vstore: VectorStoreService,
) -> None:
    kb = registry.create("手册")
    pipeline.ingest(kb.id, "faq.md", "# 密码重置\n重置步骤说明。")

    hits = vstore.search([kb.collection_name], "密码", top_k=3)
    assert hits
    assert hits[0].metadata.get("Header 1") == "密码重置"
    assert hits[0].metadata["source"] == "faq.md"


def test_chunk_metadata_has_chunk_index(
    vstore: VectorStoreService,
    registry: KBMetaStore,
) -> None:
    s = Settings(chunk_size=20, chunk_overlap=0)
    pipe = IngestionPipeline(vstore=vstore, registry=registry, settings=s)
    kb = registry.create("手册")
    pipe.ingest(kb.id, "doc.md", "一二三四五六七八九十" * 5)

    hits = vstore.search([kb.collection_name], "一", top_k=10)
    indices = sorted(h.metadata.get("chunk_index") for h in hits)
    assert indices == list(range(len(indices)))  # 0,1,2,... 连续
    assert len(indices) > 1


def test_load_markdown_cleans() -> None:
    assert load_markdown("  a\n\n\n\nb  ") == "a\n\nb"
    assert load_markdown("\n\nhello\n\n\n\n\nworld\n") == "hello\n\nworld"
    assert load_markdown("已经干净") == "已经干净"


def test_split_no_headers() -> None:
    chunks = split_document("无标题内容", "a.md", "kb1", 500, 50)

    assert len(chunks) == 1
    assert "Header 1" not in chunks[0].metadata
    assert chunks[0].metadata["source"] == "a.md"
    assert chunks[0].metadata["kb_id"] == "kb1"
    assert chunks[0].metadata["chunk_index"] == 0


def test_split_empty_text() -> None:
    assert split_document("", "a.md", "kb1", 500, 50) == []
