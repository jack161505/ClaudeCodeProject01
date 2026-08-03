"""KBMetaStore 测试：元数据 CRUD、slug 生成、文档登记与边界。"""

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

    assert kb.slug == kb.id[:8]
    assert kb.collection_name == f"kb_{kb.id[:8]}"
    assert kb.slug.isascii()


def test_slug_special_chars(store: KBMetaStore) -> None:
    kb = store.create("My/KB:1", "")

    assert "/" not in kb.slug
    assert ":" not in kb.slug
    assert "my_kb_1" in kb.slug
    assert kb.slug.isascii()


def test_create_empty_name(store: KBMetaStore) -> None:
    kb = store.create("", "")

    assert kb.slug == kb.id[:8]
    assert kb.collection_name == f"kb_{kb.id[:8]}"


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


def test_delete_then_recreate(store: KBMetaStore) -> None:
    kb1 = store.create("手册", "")
    store.delete(kb1.id)
    kb2 = store.create("手册", "")

    assert kb1.id != kb2.id
    assert kb1.collection_name != kb2.collection_name
    assert len(store.list_kbs()) == 1


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


def test_register_zero_chunks(store: KBMetaStore) -> None:
    kb = store.create("手册", "")
    store.register_document(kb.id, "a.md", 0)

    refreshed = store.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 1
    assert refreshed.chunk_count == 0


def test_unregister_document(store: KBMetaStore) -> None:
    kb = store.create("手册", "")
    store.register_document(kb.id, "a.md", 5)
    store.register_document(kb.id, "b.md", 3)
    store.unregister_document(kb.id, "a.md")

    refreshed = store.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 1
    assert refreshed.chunk_count == 3


def test_unregister_nonexistent_source_noop(store: KBMetaStore) -> None:
    kb = store.create("手册", "")
    store.register_document(kb.id, "a.md", 5)
    store.unregister_document(kb.id, "b.md")  # 不存在

    refreshed = store.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 1
    assert refreshed.chunk_count == 5


def test_register_unregister_cycle(store: KBMetaStore) -> None:
    kb = store.create("手册", "")
    store.register_document(kb.id, "a.md", 5)
    store.unregister_document(kb.id, "a.md")
    store.register_document(kb.id, "a.md", 3)

    refreshed = store.get(kb.id)
    assert refreshed is not None
    assert refreshed.document_count == 1
    assert refreshed.chunk_count == 3


def test_multiple_kbs_independent_counts(store: KBMetaStore) -> None:
    kb1 = store.create("库一", "")
    kb2 = store.create("库二", "")
    store.register_document(kb1.id, "a.md", 5)
    store.register_document(kb1.id, "b.md", 3)
    store.register_document(kb2.id, "c.md", 7)

    r1 = store.get(kb1.id)
    r2 = store.get(kb2.id)
    assert r1 is not None and r2 is not None
    assert r1.document_count == 2
    assert r1.chunk_count == 8
    assert r2.document_count == 1
    assert r2.chunk_count == 7


def test_register_document_missing_kb_raises(store: KBMetaStore) -> None:
    with pytest.raises(KnowledgeBaseNotFound):
        store.register_document("nope", "a.md", 5)


def test_persistence_across_instances(store: KBMetaStore) -> None:
    store.create("手册", "")

    fresh = KBMetaStore()  # 新实例从同一 kb_meta.json 读回
    assert len(fresh.list_kbs()) == 1
