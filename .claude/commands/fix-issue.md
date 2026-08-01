---
description: 根据问题描述定位根因并修复 bug，运行验证后总结改动
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(pytest:*), Bash(ruff:*), Bash(mypy:*), Bash(uv:*), Bash(python:*), Bash(python3:*)
---

# /fix-issue

根据问题描述定位并修复问题。用法：`/fix-issue <问题描述>`，例如 `/fix-issue 登录时密码含空格会抛 KeyError`。

## 步骤

1. **理解问题**：复述你对问题的理解 -- 现象是什么、预期行为是什么。若 `$ARGUMENTS` 描述不清，先向用户澄清，不要臆测。
2. **定位根因**：
   - 用 Grep/Glob 搜索相关代码、错误信息、关键符号
   - 阅读相关文件，追踪数据流与调用链
   - 找到**根因**，而非只处理表象
3. **说明方案**：动手前用一两句话讲清打算怎么改、为什么这样改。
4. **实施修复**：用 Edit/Write 改动最小必要范围，不要顺手重构无关代码。
5. **验证**（按项目实际工具链选择，优先 `uv run` 形式）：
   - 测试：`pytest` / `uv run pytest` / `python -m pytest`
   - lint：`ruff check` / `uv run ruff check`
   - 类型检查：`mypy` / `uv run mypy` / `mypy src`
   - 尽量构造原问题场景，确认已修复且未引入新问题
6. **总结**：列出改了哪些文件、根因是什么、如何验证的。**若测试失败，如实说明，不要谎报成功。**

不要执行 `git commit` / `git push`，除非用户明确要求。
