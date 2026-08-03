"""VectorStoreService 测试：用假 embedding 离线验证增删查、多库合并与边界。

FakeEmbeddings / vstore fixture 见 conftest.py。
"""

import pytest

from rag_cs.vectorstore.store import VectorStoreService


def test_add_and_search_single(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_one")
    vstore.add(
        collection="kb_one",
        texts=["如何重置密码", "退款流程说明", "天气查询"],
        metadatas=[{"source": "a.md"}, {"source": "b.md"}, {"source": "c.md"}],
        ids=["1", "2", "3"],
    )

    hits = vstore.search(["kb_one"], "如何重置密码", top_k=2)

    assert len(hits) == 2
    assert hits[0].content == "如何重置密码"
    assert hits[0].metadata["source"] == "a.md"
    assert all(h.collection == "kb_one" for h in hits)


def test_search_merges_multiple_collections(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_a")
    vstore.ensure_collection("kb_b")
    vstore.add("kb_a", ["密码重置A"], [{"s": "a"}], ["a1"])
    vstore.add("kb_b", ["密码重置B", "无关内容"], [{"s": "b"}, {"s": "b"}], ["b1", "b2"])

    hits = vstore.search(["kb_a", "kb_b"], "密码重置", top_k=2)

    assert len(hits) == 2
    assert {h.content for h in hits} == {"密码重置A", "密码重置B"}


def test_search_skips_missing_collection(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_x")
    vstore.add("kb_x", ["内容"], [{"s": "x"}], ["x1"])

    hits = vstore.search(["kb_x", "kb_missing"], "内容", top_k=3)

    assert len(hits) == 1
    assert hits[0].content == "内容"


def test_drop_collection(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_drop")
    vstore.add("kb_drop", ["内容"], [{"source": "drop.md"}], ["1"])
    assert vstore.collection_exists("kb_drop")

    vstore.drop_collection("kb_drop")

    assert not vstore.collection_exists("kb_drop")
    assert vstore.search(["kb_drop"], "内容", top_k=3) == []


def test_delete_by_ids(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_del")
    vstore.add("kb_del", ["保留", "删除"], [{"s": "a"}, {"s": "b"}], ["keep", "del"])

    vstore.delete("kb_del", ["del"])

    hits = vstore.search(["kb_del"], "保留", top_k=5)
    assert [h.content for h in hits] == ["保留"]


def test_delete_by_metadata(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_dm")
    vstore.add(
        "kb_dm",
        ["苹果", "香蕉", "葡萄"],
        [{"source": "x"}, {"source": "y"}, {"source": "x"}],
        ["1", "2", "3"],
    )

    vstore.delete_by_metadata("kb_dm", {"source": "x"})

    hits = vstore.search(["kb_dm"], "果", top_k=5)
    assert [h.content for h in hits] == ["香蕉"]


def test_add_length_mismatch_raises(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_m")
    with pytest.raises(ValueError, match="长度须一致"):
        vstore.add("kb_m", ["a"], [{"s": "a"}], [])


def test_empty_inputs_are_noop(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_empty")
    vstore.add("kb_empty", [], [], [])
    assert vstore.search(["kb_empty"], "q", top_k=3) == []


def test_search_top_k_zero_returns_empty(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_z")
    vstore.add("kb_z", ["内容"], [{"s": "a"}], ["1"])

    assert vstore.search(["kb_z"], "内容", top_k=0) == []


def test_search_empty_collections_returns_empty(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_e")

    assert vstore.search([], "x", top_k=3) == []


def test_search_top_k_exceeds_available(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_few")
    vstore.add("kb_few", ["甲", "乙"], [{"s": "a"}, {"s": "b"}], ["1", "2"])

    hits = vstore.search(["kb_few"], "甲", top_k=5)

    assert len(hits) == 2  # 不超过实际文档数


def test_add_duplicate_id_does_not_overwrite(vstore: VectorStoreService) -> None:
    """chromadb add 不做 upsert：同 id 再次 add 不会覆盖已有文档。

    故重新入库需先 delete_by_metadata 清旧（见 IngestionPipeline）。
    """
    vstore.ensure_collection("kb_up")
    vstore.add("kb_up", ["旧内容"], [{"source": "a"}], ["1"])
    vstore.add("kb_up", ["新内容"], [{"source": "a"}], ["1"])  # 同 id，不覆盖

    hits = vstore.search(["kb_up"], "内容", top_k=5)

    assert [h.content for h in hits] == ["旧内容"]


def test_delete_nonexistent_collection_noop(vstore: VectorStoreService) -> None:
    vstore.delete("missing_collection", ["1"])  # 不报错
    vstore.delete_by_metadata("missing_collection", {"source": "x"})


def test_search_preserves_metadata(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_meta2")
    vstore.add("kb_meta2", ["内容"], [{"source": "a.md", "section": "intro", "page": 1}], ["1"])

    hits = vstore.search(["kb_meta2"], "内容", top_k=3)

    assert hits[0].metadata["source"] == "a.md"
    assert hits[0].metadata["section"] == "intro"
    assert hits[0].metadata["page"] == 1


def test_search_sorted_by_distance(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_sort")
    vstore.add("kb_sort", ["aaa", "aab", "abc"], [{"s": "a"}] * 3, ["1", "2", "3"])

    hits = vstore.search(["kb_sort"], "aaa", top_k=3)

    assert len(hits) == 3
    scores = [h.score for h in hits]
    assert scores == sorted(scores)  # 距离升序
    assert hits[0].content == "aaa"  # 自身距离 0


def test_ensure_collection_idempotent(vstore: VectorStoreService) -> None:
    vstore.ensure_collection("kb_idem")
    vstore.ensure_collection("kb_idem")  # 重复调用不报错

    assert vstore.collection_exists("kb_idem")
