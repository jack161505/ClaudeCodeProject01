# Python 代码风格规范

本仓库的 Python 代码遵循本规范。**格式化与 lint 由 ruff 强制，类型检查由 mypy 强制**（配置见文末）。凡 ruff / mypy 能自动管的，以工具配置为准；本文档只补充工具管不到、或需要人为判断的部分。

> 默认目标 Python 3.11+。若实际版本不同，调整文末 `target-version` / `python_version` 及第 4 节的泛型写法。

## 1. 总原则

- **可读性优先**，聪明次于清晰
- **显式优于隐式**：不靠副作用、不用魔法
- **一致性**：历史代码与本文档冲突时，以本文档为准

## 2. 格式化（ruff format，black 兜底）

- 行宽 **100**
- 缩进 4 空格，禁用 Tab
- 双引号优先（与 ruff format 默认一致）
- 行尾不留空格，文件末尾保留一个换行
- import 排序交给 ruff (isort)，**不要手动调**
- 函数 / 类之间空两行，方法之间空一行

## 3. 命名

| 对象 | 风格 | 示例 |
|---|---|---|
| 变量、函数、方法 | snake_case | `user_count`、`parse_config` |
| 类 | PascalCase | `HttpClient` |
| 常量 | UPPER_SNAKE | `MAX_RETRIES` |
| 模块文件 | lower_snake | `user_service.py` |
| 私有成员 | 前缀下划线 | `_internal_cache` |
| 类型变量 | PascalCase | `T`、`UserT` |

- 避免单字母命名（循环索引 `i/j/k`、数学符号除外）
- 布尔变量加 `is_` / `has_` / `should_` 前缀：`is_active`

## 4. 类型注解

- 所有 public 函数 / 方法**必须**标注参数与返回类型
- 容器类型用小写泛型：`list[str]`、`dict[str, int]`（Python 3.9+）
- 可选值用 `X | None`（Python 3.10+），不用 `Optional[X]`
- 避免裸 `Any`；确需使用须注释说明为何无法标注
- 复杂签名考虑用 `TypedDict` / `Protocol` / `dataclass` 建模，而非堆 dict

## 5. import 顺序（ruff 自动）

1. 标准库
2. 第三方
3. 本项目内部

每组内字母序，组间空一行。

## 6. 异常处理

- 捕获**具体**异常，禁止裸 `except:` 与 `except Exception:` 吞错
- 不要捕获后什么都不做；至少记录日志
- 自定义异常继承项目基类异常，按层级组织
- 用异常表达"预期外的失败"，用返回值 / 类型表达"预期的非结果"（如返回 `None`）

## 7. 函数与结构

- 函数短小、单一职责；超过约 40 行考虑拆分
- 参数避免超过 5 个；多了用 `dataclass` 或关键字参数
- **禁止可变默认参数**：

  ```python
  # ❌
  def add_item(item, cache=[]):
      cache.append(item)

  # ✅
  def add_item(item, cache=None):
      cache = [] if cache is None else cache
      cache.append(item)
  ```

- 模块顶层只放 import、常量、定义；副作用代码放进 `if __name__ == "__main__":`

## 8. 文档字符串

- public 的模块、类、函数写 docstring，内部私有的可省
- 统一用 **Google 风格**：

  ```python
  def fetch_user(user_id: str) -> User:
      """获取单个用户。

      Args:
          user_id: 用户唯一标识。

      Returns:
          User 对象。

      Raises:
          NotFoundError: 用户不存在时。
      """
  ```

- 注释解释**为什么**，不解释"是什么"——代码本身能说明的不要重复

## 9. 测试（pytest）

- 文件 `test_*.py`，函数 `test_*`，测试类 `Test*`
- 一个测试只验证一个行为，命名描述被测行为：`test_login_rejects_empty_password`
- 用 **AAA 结构**：Arrange / Act / Assert，空行分隔
- 用 fixture 管理共享 setUp，避免测试间隐式依赖
- 测**公开行为**，不测私有实现细节

## 10. 注释与 TODO

- TODO 格式：`# TODO(name): 描述`，如 `# TODO(jack): 改为批量查询`
- 调试用 `print`、注释掉的代码不要提交

---

## 附：ruff / mypy 配置（`pyproject.toml`）

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]
# E/F = pycodestyle + pyflakes, I = isort, UP = pyupgrade,
# B = bugbear, SIM = simplify, RUF = ruff 自身规则

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
```
