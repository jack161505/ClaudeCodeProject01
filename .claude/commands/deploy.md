---
description: 检测部署方式并执行部署（发布前必确认，绝不自动推送生产）
allowed-tools: Read, Glob, Grep, Bash(git status:*), Bash(git log:*), Bash(pytest:*), Bash(ruff:*), Bash(uv:*), Bash(pip install:*), Bash(python:*)
---

# /deploy

将当前项目部署到目标环境。用法：`/deploy [环境]`，环境如 `staging`、`prod`（默认 `staging`）。

⚠️ 部署是对外、难以撤销的操作。**任何实际发布命令（docker push / serverless deploy / sam deploy / fly deploy / ssh 等）执行前，必须先向用户确认**，说明将运行什么、影响哪个环境。

## 步骤

1. **确认环境**：解析 `$ARGUMENTS`，缺省为 `staging`。若为 `prod` / `production`，再次强调风险并要求显式确认。
2. **检测部署方式**（按项目里存在的文件判断）：
   - `Dockerfile` / `docker-compose.yml` -> 容器化部署（构建镜像、推 registry 或服务器运行）
   - `serverless.yml` -> Serverless Framework（AWS Lambda 等）
   - `template.yaml` -> AWS SAM（Lambda）
   - `zappa_settings.json` / `.chalice/` -> AWS Lambda（Python 专属：Zappa / Chalice）
   - `Procfile` -> Heroku / Render / Fly 等基于进程的 PaaS
   - `fly.toml` / `render.yaml` / `railway.json` / `app.json` -> 对应平台
   - `.github/workflows/*.yml` -> 通过 CI 触发（说明流程，不直接发布）
   - 都没有 -> **停止**，询问用户目标平台并给出最小配置建议
3. **发布前检查**：
   - `git status` 确认工作区状态（干净，或带着有意识的改动）
   - 同步依赖：`uv sync` 或 `pip install -e .` 或 `pip install -r requirements.txt`
   - lint：`ruff check`
   - 测试：`pytest`
   - 若需打包产物：`python -m build`（生成 sdist/wheel）
   - 任一步失败则**中止部署**并报告，不要继续
4. **确认后发布**：向用户展示即将执行的确切命令，得到确认后再运行实际发布步骤。
5. **报告结果**：成功 -> 给出访问地址 / 产物位置；失败 -> 附上错误日志与排查建议。

绝不把密钥、`.env`、个人配置打包进产物或推送到远端。
