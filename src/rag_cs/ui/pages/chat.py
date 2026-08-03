"""智能客服对话页：流式输出 + 展示工具调用过程。"""

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from rag_cs.agent.graph import AgentEvent, AgentEventType, AgentService
from rag_cs.kb.registry import KBMetaStore
from rag_cs.ui.state import add_chat_message, get_chat_messages, get_enabled_kb_ids


def render() -> None:
    st.header("智能客服")

    enabled_ids = get_enabled_kb_ids()
    kbs = KBMetaStore().list_kbs()
    collections = [kb.collection_name for kb in kbs if kb.id in enabled_ids]
    if not collections:
        st.info("请在侧边栏勾选至少一个知识库后再对话。")

    for msg in get_chat_messages():
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("请输入问题")
    if not prompt:
        return
    if not collections:
        st.warning("未启用任何知识库。")
        return

    with st.chat_message("user"):
        st.markdown(prompt)
    add_chat_message("user", prompt)

    with st.chat_message("assistant"):
        answer_box = st.empty()
        tool_box = st.container()
        answer_parts: list[str] = []
        svc = AgentService()
        with st.spinner("思考中…"):
            for event in svc.stream(collections, prompt):
                _handle_event(event, tool_box, answer_parts, answer_box)
        add_chat_message("assistant", "".join(answer_parts))


def _handle_event(
    event: AgentEvent,
    tool_box: DeltaGenerator,
    answer_parts: list[str],
    answer_box: DeltaGenerator,
) -> None:
    if event.type is AgentEventType.TOOL_CALL:
        with tool_box:
            st.info(f"🔍 检索知识库：{event.query or ''}")
    elif event.type is AgentEventType.TOOL_RESULT:
        with tool_box, st.expander("检索结果", expanded=False):
            st.text(event.content)
    elif event.type is AgentEventType.TOKEN:
        answer_parts.append(event.content)
        answer_box.markdown("".join(answer_parts))
