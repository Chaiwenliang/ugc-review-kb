"""演示：LLM 翻译器 + 策略引擎 联动。
输入一句人话规则 → AI 生成策略建议 → 用引擎试跑验证。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from review.llm_translator import LLMTranslator
from review.engine import ReviewEngine
from review.wordlist import WordlistEngine


def main():
    # 1. 配好 LLM 翻译器（Qwen，OpenAI 接口）
    翻译器 = LLMTranslator(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # Qwen 兼容接口
        model="qwen3.5-flash",
    )

    # 2. 用户输入一句"人话规则"
    用户规则 = input("请描述你的治理规则（例如：广告太多，管严点，但别误伤正常用户）：\n> ")

    # 3. AI 生成策略建议
    print("\n🔍 AI 正在分析规则，生成策略建议...")
    建议 = 翻译器.生成策略建议(用户规则)
    print("\n📋 AI 建议的策略配置：")
    print(json.dumps(建议, ensure_ascii=False, indent=2))

    # 4. 说明：这是"建议"，需人工确认后才落地
    print("\n✅ 这是 AI 生成的策略建议。下一步可：")
    print("   a) 人工确认/微调后，写入词表配置")
    print("   b) 用引擎试跑验证（见 run_demo.py）")
    print("   c) 调整规则重试")


if __name__ == "__main__":
    import json
    main()