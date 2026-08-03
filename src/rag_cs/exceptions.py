"""项目异常基类层级。

所有自定义异常继承 RagCsError，按子模块组织下级异常
（如 kb.KnowledgeBaseNotFound），便于上层按基类统一捕获。
"""


class RagCsError(Exception):
    """所有项目自定义异常的基类。"""
