"""Streamlit 入口：侧边栏路由 + 全局启用知识库多选。"""

import streamlit as st

from rag_cs.kb.registry import KBMetaStore
from rag_cs.ui import state
from rag_cs.ui.pages import chat, kb_management


def main() -> None:
    st.set_page_config(page_title="RAG 智能客服", page_icon="🛠", layout="wide")
    st.title("RAG 智能客服系统")

    with st.sidebar:
        page = st.radio("页面", ["知识库管理", "智能客服"])
        st.divider()
        st.subheader("启用的知识库")
        _render_enabled_selector()

    if page == "知识库管理":
        kb_management.render()
    else:
        chat.render()


def _render_enabled_selector() -> None:
    kbs = KBMetaStore().list_kbs()
    if not kbs:
        st.caption("暂无知识库，请先在「知识库管理」创建。")
        return
    options = {
        kb.id: f"{kb.name}（{kb.document_count} 文档 / {kb.chunk_count} 片段）" for kb in kbs
    }
    enabled = state.get_enabled_kb_ids()
    default = [kid for kid in enabled if kid in options]
    chosen = st.multiselect(
        "选择对话时启用的知识库",
        options=list(options.keys()),
        default=default,
        format_func=lambda kid: options.get(kid, kid),
    )
    state.set_enabled_kb_ids(chosen)


if __name__ == "__main__":
    main()
