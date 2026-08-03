"""手动验证 providers 连通性。

先 uv sync 并配好 .env，然后运行：
    uv run python scripts/check_providers.py

会按当前 .env 配置的 chat_provider / embedding_provider 各发一次请求。
"""

from rag_cs.config import get_settings
from rag_cs.providers.factory import get_chat_model, get_embeddings


def check_chat() -> bool:
    s = get_settings()
    print(f"[chat] provider={s.chat_provider.value} model={s.chat_model}")
    try:
        resp = get_chat_model(s).invoke("说一个字：好")
        print(f"  ✓ 回复: {resp.content!r}")
        return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False


def check_embeddings() -> bool:
    s = get_settings()
    print(f"[embedding] provider={s.embedding_provider.value} model={s.embedding_model}")
    try:
        vec = get_embeddings(s).embed_query("你好")
        print(f"  ✓ 维度: {len(vec)}  前5维: {vec[:5]}")
        return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False


if __name__ == "__main__":
    ok1 = check_chat()
    ok2 = check_embeddings()
    if ok1 and ok2:
        print("✓ providers 连通性验证通过")
    else:
        print("✗ 部分验证失败，见上")
