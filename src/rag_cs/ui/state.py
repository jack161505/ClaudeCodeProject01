"""Streamlit session_state 读写封装，集中管理 key 与类型。"""

from typing import TypedDict, cast

import streamlit as st


class ChatMessage(TypedDict):
    """对话历史中的一条消息。"""

    role: str  # "user" | "assistant"
    content: str


_ENABLED_KEY = "enabled_kb_ids"
_CHAT_KEY = "chat_messages"


def get_enabled_kb_ids() -> list[str]:
    """本次对话启用的知识库 id 列表。"""
    if _ENABLED_KEY in st.session_state:
        val = st.session_state[_ENABLED_KEY]
        if isinstance(val, list):
            return cast("list[str]", val)
    return []


def set_enabled_kb_ids(kb_ids: list[str]) -> None:
    st.session_state[_ENABLED_KEY] = kb_ids


def get_chat_messages() -> list[ChatMessage]:
    """对话历史。"""
    if _CHAT_KEY in st.session_state:
        val = st.session_state[_CHAT_KEY]
        if isinstance(val, list):
            return cast("list[ChatMessage]", val)
    return []


def add_chat_message(role: str, content: str) -> None:
    msgs = get_chat_messages()
    msgs.append(ChatMessage(role=role, content=content))
    st.session_state[_CHAT_KEY] = msgs


def clear_chat() -> None:
    st.session_state[_CHAT_KEY] = []
