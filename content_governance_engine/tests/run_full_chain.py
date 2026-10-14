"""全链路演示：词表 → 用户分层 → 模型层（用模拟模型，不烧配额）。
验证引擎完整判定路径，不依赖真实 LLM。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from review.wordlist import WordlistEngine
from review.engine import ReviewEngine
from review.model_layer import MockModelLayer


def main():
    词表 = WordlistEngine("config/wordlist.json")
    模型 = MockModelLayer()          # 用模拟模型层，无 key 也能跑
    engine = ReviewEngine(词表, 模型)

    print("=== 全链路演示（词表→用户分层→模型层）===\n")

    测试集 = [
        # (内容, 用户画像)
        ("你这个傻逼", {"违规次数": 1, "消费额": 10}),                      # 命中必杀→直接拦
        ("加我微信低价出", {"违规次数": 0, "消费额": 200}),                 # 命中打压→白名单降权
        ("呵呵，就你也配发帖", {"违规次数": 3, "消费额": 0}),              # 词表拦不住→模型判阴阳→降权
        ("你水平这么高，我们学不来", {"违规次数": 5, "消费额": 0}),        # 阴阳→模型判→降权
        ("今天天气不错，周末去爬山", {"违规次数": 0, "消费额": 0}),         # 正常→模型判正常→放行
        ("你妈死了赶紧滚", {"违规次数": 6, "消费额": 0}),                   # 命中必杀+黑名单→拦截
    ]

    for text, profile in 测试集:
        r = engine.judge(text, profile)
        src = "词表" if r["source"] == "wordlist" else "模型"
        print(f"内容: {text!s:<22} 用户层:{r['user_level']:<5} 处置:{r['action']:<6} 来源:{src:<3} 依据:{r['detail']}")

    print("\n✅ 全链路跑通。说明：")
    print("  · 词表能拦的（必杀/打压）→ 直接处置，不花模型钱")
    print("  · 词表拦不住的（阴阳/语义）→ 交给模型层判语义")
    print("  · 用户分层贯穿全程，同内容不同用户处置不同")


if __name__ == "__main__":
    main()