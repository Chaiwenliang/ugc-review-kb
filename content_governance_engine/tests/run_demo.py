"""演示：加载词表 → 试跑几条内容 → 看处置结果"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from review.wordlist import WordlistEngine
from review.engine import ReviewEngine

# 加载词表
wordlist = WordlistEngine("config/wordlist.json")
engine = ReviewEngine(wordlist)

# 试跑几条内容
测试集 = [
    ("加VX领取红包", {"违规次数": 0, "消费额": 200}),    # 白名单 命中打压 → 降权
    ("加微信聊", {"违规次数": 3, "消费额": 10}),         # 风险   命中打压 → 限流
    ("这是涉政词A", {"违规次数": 0, "消费额": 0}),        # 普通   命中必杀 → 拦截
    ("今天天气不错", {"违规次数": 0, "消费额": 0}),       # 普通   未命中 → 放行
    ("疑似广告", {"违规次数": 0, "消费额": 0}),           # 普通   命中观察 → 放行模型
]

for text, profile in 测试集:
    result = engine.judge(text, profile)
    print(f"内容: {text:<12} 用户层: {result['user_level']:<5} 处置: {result['action']:<6} 依据: {result['detail']}")