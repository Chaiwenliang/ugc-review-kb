"""指标看板演示 v2：真实抽样口径。
只随机抽检一部分记录(带真值)算漏判/误判率，其余只记录不真值。
模拟一处漏判(违规被放行)，看漏判率能正确反映。
"""
import sys
import random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from review.wordlist import WordlistEngine
from review.engine import ReviewEngine
from review.model_layer import MockModelLayer
from review.metrics import MetricsEngine


def main():
    random.seed(1)   # 固定随机种子，结果可复现
    词表 = WordlistEngine("config/wordlist.json")
    模型 = MockModelLayer()
    engine = ReviewEngine(词表, 模型)
    metrics = MetricsEngine("config/review_records.json")

    print("=== 指标看板演示 v2（真实抽样口径）===\n")

    # 一批内容：真值标注"违规/正常"
    数据集 = [
        # (内容, 用户画像, 人工真值)
        ("加我微信", {"违规次数": 0, "消费额": 200}, "违规"),   # 白名单降权→正确拦
        ("你这个傻逼", {"违规次数": 0, "消费额": 500}, "违规"), # 必杀拦截→正确拦
        ("今天天气不错", {"违规次数": 0, "消费额": 0}, "正常"), # 放行→正确放
        ("呵呵，就你也配", {"违规次数": 0, "消费额": 0}, "违规"), # 阴阳→降权→正确拦
        ("加我微信", {"违规次数": 2, "消费额": 0}, "违规"),    # 风险拦截→正确拦
        ("好货低价出", {"违规次数": 0, "消费额": 0}, "违规"),  # 普通限流→正确拦
        ("真心感谢帮忙", {"违规次数": 0, "消费额": 0}, "正常"), # 放行→正确放
        ("正常交流没毛病", {"违规次数": 0, "消费额": 0}, "正常"), # 放行→正确放
        ("你妈", {"违规次数": 1, "消费额": 0}, "违规"),        # 必杀拦截→正确拦
        ("加V", {"违规次数": 0, "消费额": 0}, "违规"),         # 普通限流→正确拦
        # 下面这条"阴阳"模拟模型漏判：真值违规，但模型判正常放行
        ("嗯嗯你说得都对呢", {"违规次数": 0, "消费额": 0}, "违规"), # 应拦，但mock模型可能漏→漏判
    ]

    # 只随机抽检 50% 的记录（其余不填真值，不算漏判/误判）
    抽检比例 = 0.5
    for i, (text, profile, truth) in enumerate(数据集):
        result = engine.judge(text, profile)
        sampled = random.random() < 抽检比例   # 是否被抽检
        metrics.record(result, text, ground_truth=truth, sampled=sampled)

    print("已记录", len(数据集), "条审核结果。\n")
    print("--- 指标看板 ---")
    print(metrics.pretty_summary())

    print("\n--- 明细（全部）---")
    for r in metrics.records:
        sam = "✅抽检" if r["sampled"] else " 未抽"
        print(f"{sam} 处置:{r['action']:<4} 来源:{r['source']:<4} 真值:{str(r['ground_truth']):<4} 依据:{r['detail'][:28]}")

    print("\n说明：只有被抽检的记录(带真值)才进入漏判/误判率计算；未抽检的不影响指标。")


if __name__ == "__main__":
    main()