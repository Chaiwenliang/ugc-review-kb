"""演示：LLM 翻译器（带澄清追问版）——从环境变量读 base_url/model/key"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from review.llm_translator import LLMTranslator, 交互翻译

def main():
    翻译器 = LLMTranslator()   # 全部从环境变量读
    交互翻译(翻译器)

if __name__ == "__main__":
    main()