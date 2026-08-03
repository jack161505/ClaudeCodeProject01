"""KBMetaStore 测试：元数据 CRUD 与文档登记，落临时 kb_meta.json。

不依赖 chroma，纯文件 I/O；数据路径走 conftest 的 tmp_data_dir。
"""

from pathlib import Path

import pytest

from rag_cs.kb.registry import KBMetaStore, KnowledgeBaseNotFound


@pytest.fixture
def store(tmp_data_dir: Path) -> KBMetaStore:
    return KBMetaStore()


def test_create_and_list(store: KBMetaStore) -> None:
    kb = store.create("产品手册", "产品文档")

    assert kb.name == "产品手册"
    assert kb.description == "产品文档"
    assert kb.id
    assert kb.collection_name.startswith("kb_")
    assert kb.created_at
    assert kb.document_count == 0
    assert kb.chunk_count == 0

    listed = store.list_kbs()
    assert [k.id for k in listed] == [kb.id]


def test_ascii_name_slugified(store: KBMetaStore) -> None:
    kb = store.create("My Product Manual", "")

    assert kb.slug == f"my_product_manual_{kb.id[:8]}"
    assert kb.collection_name == f"kb_my_product_manual_{kb.id[:8]}"


def test_chinese_name_falls_back_to_short_id(store: KBMetaStore) -> None:
    kb = store.create("客服知识库", "")
    # 纯中文名无 ASCII 部分，slug 回退为短 id，collection_name 仍合法 ASCII
    assert kb.slug == kb.id[:8]
    assert kb.collection_name == f"kb_{kb.id[:8]}"
    assert kb.slug.isascii()


def test_duplicate_names_get_unique_collections(store: KBMetaStore) -> None:
    a = store.create("手册", "")
    b = store.create("手册", "")

    assert a.id != b.id
    assert a.collection_name != b.collection_name


def test_get_existing_and_missing(store: KBMetaStore) -> None:
    kb = store.create("手册", "")

    assert store.get(kb.id) is not None
    assert store.get("nope") is None


def test_delete_returns_kb_and_removes(store: KBMetaStore) -> None:
    kb = store.create("手册", "")

    removed = store.delete(kb.id)
    assert removed is not None
    assert removed.id == kb.id
    assert store.get(kb.id) is None
    assert store.delete("nope") is None


def test_register_new_document_updates_counts(store: KBMetaStore) -> None:
    kb = store.create("手册", "")
    store.register_document(kb.id, "a.md", chunk_count=5)

    refreshed = store.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 1
    assert refreshed.chunk_count == 5


def test_register_same_source_updates_chunk_count(store: KBMetaStore) -> None:
    kb = store.create("手册", "")
    store.register_document(kb.id, "a.md", chunk_count=5)
    store.register_document(kb.id, "a.md", chunk_count=8)  # 重新入库

    refreshed = store.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 1  # 仍是同一份文档
    assert refreshed.chunk_count == 8


def test_unregister_document(store: KBMetaStore) -> None:
    kb = store.create("手册", "")
    store.register_document(kb.id, "a.md", 5)
    store.register_document(kb.id, "b.md", 3)
    store.unregister_document(kb.id, "a.md")

    refreshed = store.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 1
    assert refreshed.chunk_count == 3


def test_register_document_missing_kb_raises(store: KBMetaStore) -> None:
    with pytest.raises(KnowledgeBaseNotFound):
        store.register_document("nope", "a.md", 5)


def test_persistence_across_instances(store: KBMetaStore) -> None:
    store.create("手册", "")

    fresh = KBMetaStore()  # 新实例从同一 kb_meta.json 读回
    assert len(fresh.list_kbs()) == 1
