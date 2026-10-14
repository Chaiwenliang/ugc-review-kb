"""全链路演示 v2：词表→用户分层→模型（含动态用户分层处置）。用模拟模型，不烧配额。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from review.wordlist import WordlistEngine
from review.engine import ReviewEngine
from review.model_layer import MockModelLayer


def main():
    词表 = WordlistEngine("config/wordlist.json")
    模型 = MockModelLayer()
    engine = ReviewEngine(词表, 模型)

    print("=== 全链路演示 v2（含动态用户分层处置）===\n")

    测试集 = [
        # (内容, 用户画像)  说明
        # --- 动态分层：同是"加微信"，不同违规次数处置不同 ---
        ("加我微信", {"违规次数": 0, "消费额": 200}),    # 白名单老用户 → 降权（宽容）
        ("加我微信", {"违规次数": 0, "消费额": 0}),     # 普通首犯 → 限流观察
        ("加我微信", {"违规次数": 2, "消费额": 0}),      # 风险 → 拦截（从严）
        ("加我微信", {"违规次数": 6, "消费额": 0}),      # 黑名单 → 拦截（最严）

        # --- 红线：必杀词不看用户层 ---
        ("你这个傻逼", {"违规次数": 0, "消费额": 500}),  # 即使老用户，红线也拦
        ("你妈死了", {"违规次数": 6, "消费额": 0}),     # 黑名单，必杀

        # --- 模型层：词表拦不住的语义 ---
        ("呵呵，就你也配发帖", {"违规次数": 1, "消费额": 0}),  # 阴阳→模型判→降权
        ("今天天气不错", {"违规次数": 0, "消费额": 0}),        # 正常→放行
    ]

    for text, profile in 测试集:
        r = engine.judge(text, profile)
        src = "词表" if r["source"] == "wordlist" else "模型"
        print(f"内容: {text!s:<14} 违规次数:{profile.get('违规次数',0):<2} 用户层:{r['user_level']:<5} 处置:{r['action']:<6} 来源:{src:<3} 依据:{r['detail']}")

    print("\n✅ 说明：")
    print("  · 打压词（广告/引流）→ 动态分层：老用户降权、普通限流、风险/黑名单拦截")
    print("  · 必杀词（红线辱骂）→ 不看用户层，直接拦")
    print("  · 词表拦不住的（阴阳）→ 模型层判语义")


if __name__ == "__main__":
    main()