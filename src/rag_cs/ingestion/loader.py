"""Markdown 文档加载与清洗。

UI 直接传入已解码的文本（file_uploader 的内容），本模块只做规整。
"""

import re


def load_markdown(text: str) -> str:
    """清洗 Markdown 文本：去首尾空白，3 个以上换行压成 2 个。

    Args:
        text: Markdown 原文。

    Returns:
        规整后的文本。
    """
    return re.sub(r"\n{3,}", "\n\n", text.strip())
