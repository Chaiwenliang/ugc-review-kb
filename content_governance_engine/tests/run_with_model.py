"""模型层试跑：验证 LLM 多分类能否判出"词表拦不住"的语义内容。
测 4 类内容：阴阳怪气（词表拦不住）、正常、广告、辱骂。
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from review.model_layer import LLMModelLayer


def main():
    模型 = LLMModelLayer()
    print("=== 模型层多分类试跑 ===\n")

    测试集 = [
        "你水平这么高，我们可真是学不来呢",      # 阴阳怪气（无脏词，但讽刺）
        "今天天气不错，周末去爬山",              # 正常
        "加我微信低价出，扫码领红包",            # 广告
        "你这个傻逼，滚远点",                    # 辱骂
        "呵呵，就你这种人也配发帖",              # 阴阳（讽刺）
        "真心感谢你上次的帮忙，学到了很多",      # 正常（表扬）
    ]

    for text in 测试集:
        print(f"内容: {text}")
        try:
            结果 = 模型.classify(text)
            print(f"  → 分类: {结果.get('分类'):<4} 置信度: {结果.get('置信度'):<5} 违规: {结果.get('是否违规')} | {结果.get('理由','')}")
        except Exception as e:
            print(f"  ❌ 调用失败: {e}")
        print()
        time.sleep(1)   # 每条间隔1s，避免触发并发限流


if __name__ == "__main__":
    main()