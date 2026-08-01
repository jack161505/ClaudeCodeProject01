#!/usr/bin/env bash
# PostToolUse hook: 在 Claude 写入/编辑文件后自动格式化。
# 防御式设计 -- 仅当本机装了对应 formatter 时才执行，否则静默跳过（exit 0）。
# Claude Code 会把 hook 事件以 JSON 形式从 stdin 传入，其中含 tool_input.file_path。

set -uo pipefail

input=$(cat)

# 从 stdin JSON 中提取 file_path：优先 jq，回退 python3
if command -v jq >/dev/null 2>&1; then
  file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
else
  file_path=$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)
fi

[ -z "$file_path" ] && exit 0
[ -f "$file_path" ] || exit 0

# 按扩展名选择 formatter；工具不存在则跳过
case "$file_path" in
  *.js|*.jsx|*.ts|*.tsx|*.json|*.jsonc|*.css|*.scss|*.md|*.yaml|*.yml)
    command -v prettier >/dev/null 2>&1 && prettier --write "$file_path" >/dev/null 2>&1 || true
    ;;
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format "$file_path" >/dev/null 2>&1 || true
    elif command -v uv >/dev/null 2>&1 && [ -f pyproject.toml ]; then
      uv run ruff format "$file_path" >/dev/null 2>&1 || true
    elif command -v black >/dev/null 2>&1; then
      black -q "$file_path" >/dev/null 2>&1 || true
    fi
    ;;
  *.go)
    command -v gofmt >/dev/null 2>&1 && gofmt -w "$file_path" >/dev/null 2>&1 || true
    ;;
esac

exit 0
