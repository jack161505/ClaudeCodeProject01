---
description: 分析当前改动并生成一次规范的 Git 提交
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git branch:*), Bash(git rev-parse:*)
---

# /commit

请按以下步骤为本仓库创建一次提交：

1. 用 `git status` 与 `git diff`（必要时 `git diff --staged`）查看全部改动
2. 若当前在 main/master 分支，先询问是否要新建分支再提交
3. 将改动总结成一条简洁的中文 commit message，格式：`<类型>: <描述>`
   - 类型从 feat / fix / docs / style / refactor / perf / test / chore 中选
4. `git add` 相关文件 —— 不要提交密钥、`.env`、日志等不该入库的内容
5. `git commit` 完成提交

除非用户明确要求，不要执行 `git push`。
