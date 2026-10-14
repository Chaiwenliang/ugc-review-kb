"""指标看板演示：跑一批内容→记录审核结果→聚合指标（漏判/误判/介入率）。
用模拟模型，不烧配额。展示平台"可观测、可复盘"能力。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from review.wordlist import WordlistEngine
from review.engine import ReviewEngine
from review.model_layer import MockModelLayer
from review.metrics import MetricsEngine


def main():
    词表 = WordlistEngine("config/wordlist.json")
    模型 = MockModelLayer()
    engine = ReviewEngine(词表, 模型)
    metrics = MetricsEngine("config/review_records.json")

    print("=== 指标看板演示（跑一批内容，聚合指标）===\n")

    # 一批测试内容：每条带"人工真值"(ground_truth)用于算漏判/误判
    数据集 = [
        # (内容, 用户画像, 人工真值)
        ("加我微信", {"违规次数": 0, "消费额": 200}, "违规"),   # 白名单降权 → 正确拦
        ("你这个傻逼", {"违规次数": 0, "消费额": 500}, "违规"), # 必杀拦截 → 正确拦
        ("今天天气不错", {"违规次数": 0, "消费额": 0}, "正常"), # 放行 → 正确放
        ("呵呵，就你也配", {"违规次数": 0, "消费额": 0}, "违规"), # 阴阳→降权 → 正确拦
        ("加我微信", {"违规次数": 2, "消费额": 0}, "违规"),    # 风险拦截 → 正确拦
        ("好货低价出", {"违规次数": 0, "消费额": 0}, "违规"),  # 普通限流 → 正确拦
        ("真心感谢帮忙", {"违规次数": 0, "消费额": 0}, "正常"), # 放行 → 正确放
        ("正常交流没毛病", {"违规次数": 0, "消费额": 0}, "正常"), # 放行 → 正确放
        ("你妈", {"违规次数": 1, "消费额": 0}, "违规"),        # 必杀拦截 → 正确拦
        ("加V", {"违规次数": 0, "消费额": 0}, "违规"),         # 普通限流 → 正确拦
    ]

    for text, profile, truth in 数据集:
        result = engine.judge(text, profile)
        metrics.record(result, text, ground_truth=truth)

    print("已记录", len(数据集), "条审核结果。\n")
    print("--- 指标看板 ---")
    print(metrics.pretty_summary())

    print("\n--- 明细（前5条）---")
    for r in metrics.records[:5]:
        print(f"  处置:{r['action']:<4} 来源:{r['source']:<4} 真值:{r['ground_truth']} 依据:{r['detail'][:30]}")


if __name__ == "__main__":
    main()