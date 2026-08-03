"""知识库管理页：新建、上传 Markdown 入库、列表与删除。"""

import streamlit as st

from rag_cs.ingestion.pipeline import IngestionPipeline
from rag_cs.kb.models import KnowledgeBase
from rag_cs.kb.registry import KBMetaStore
from rag_cs.vectorstore.store import VectorStoreService


def render() -> None:
    st.header("知识库管理")
    registry = KBMetaStore()
    vstore = VectorStoreService()
    pipeline = IngestionPipeline(vstore=vstore, registry=registry)

    _render_create(registry, vstore)
    st.divider()
    _render_upload(registry, pipeline)
    st.divider()
    _render_list(registry, vstore)


def _render_create(registry: KBMetaStore, vstore: VectorStoreService) -> None:
    st.subheader("新建知识库")
    with st.form("create_kb", clear_on_submit=True):
        name = st.text_input("名称")
        desc = st.text_area("描述（可选）")
        if st.form_submit_button("创建") and name.strip():
            kb = registry.create(name.strip(), desc.strip())
            vstore.ensure_collection(kb.collection_name)
            st.success(f"已创建：{kb.name}（collection={kb.collection_name}）")
            st.rerun()


def _render_upload(registry: KBMetaStore, pipeline: IngestionPipeline) -> None:
    st.subheader("上传 Markdown 文档")
    kbs = registry.list_kbs()
    if not kbs:
        st.info("请先创建知识库。")
        return
    options = {kb.id: kb.name for kb in kbs}
    kb_id = st.selectbox(
        "目标知识库",
        options=list(options.keys()),
        format_func=lambda kid: options.get(kid, kid),
    )
    files = st.file_uploader(
        "选择 Markdown 文件",
        type=["md", "markdown"],
        accept_multiple_files=True,
    )
    if files and st.button("入库") and kb_id is not None:
        for f in files:
            text = f.read().decode("utf-8")
            n = pipeline.ingest(kb_id, f.name, text)
            st.success(f"{f.name}：入库 {n} 个片段")
        st.rerun()


def _render_list(registry: KBMetaStore, vstore: VectorStoreService) -> None:
    st.subheader("知识库列表")
    kbs = registry.list_kbs()
    if not kbs:
        st.caption("暂无知识库。")
        return
    for kb in kbs:
        _render_kb_item(kb, registry, vstore)


def _render_kb_item(
    kb: KnowledgeBase,
    registry: KBMetaStore,
    vstore: VectorStoreService,
) -> None:
    with st.expander(f"{kb.name}（{kb.document_count} 文档 / {kb.chunk_count} 片段）"):
        st.write(f"**ID**：`{kb.id}`")
        st.write(f"**Collection**：`{kb.collection_name}`")
        if kb.description:
            st.write(f"**描述**：{kb.description}")
        if kb.documents:
            st.write("**文档**：")
            for doc in kb.documents:
                st.write(f"- {doc.source}（{doc.chunk_count} 片段）")
        if st.button("删除", key=f"del_{kb.id}"):
            registry.delete(kb.id)
            vstore.drop_collection(kb.collection_name)
            st.success(f"已删除：{kb.name}")
            st.rerun()
