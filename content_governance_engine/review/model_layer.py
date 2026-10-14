"""模型策略层：多分类语义判断（接 LLM）。
输入：文本内容 → 输出：分类 + 置信度 + 是否违规。
走 OpenAI 兼容接口，key/base_url/model 从环境变量读。
带失败重试 + 限流控制（处理 429 并发受限）。
"""
import os
import json
import time
from openai import OpenAI


class LLMModelLayer:
    def __init__(self, base_url=None, api_key=None, model=None, max_retries=3, retry_delay=2.0):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "DeepSeek-V4-Flash-0731")
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if not self.api_key:
            raise ValueError("缺少 API Key：请设置环境变量 LLM_API_KEY 或传入 api_key")

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=60.0)

    # 核心：多分类语义判断（带重试）
    def classify(self, text: str) -> dict:
        """返回: {"分类": "正常/辱骂/广告/阴阳", "置信度": 0.87, "是否违规": true/false, "理由": "..."}"""
        system = """你是内容审核的语义分类器。判断一段文本属于哪一类，以及是否违规。

分类只能是以下之一：正常、辱骂、广告、阴阳。
- 正常：日常交流，无不文明内容
- 辱骂：直接的攻击、辱骂、人身攻击
- 广告：引流、推广、导流（如加微信、低价、扫码）
- 阴阳：阴阳怪气、含沙射影、隐晦攻击（没有脏词但带恶意/讽刺）

规则：
- "是否违规"为 true 当且仅当分类不是"正常"。
- 置信度：0~1，你对判断的把握程度。

只输出JSON，不要多余文字：
{"分类": "...", "置信度": 0.0, "是否违规": true/false, "理由": "一句话说明"}"""

        for attempt in range(self.max_retries):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": text},
                    ],
                    response_format={"type": "json_object"},
                )
                return json.loads(resp.choices[0].message.content)
            except Exception as e:
                # 429/限流 → 等一会重试；其他错误也重试，最后抛出
                is_rate = "429" in str(e) or "limit" in str(e).lower() or "rate" in str(e).lower()
                wait = self.retry_delay * (attempt + 1)
                print(f"  ⚠️ 第{attempt+1}次失败({type(e).__name__})，等待{wait}s重试...", file=None)
                time.sleep(wait)
                if attempt == self.max_retries - 1:
                    raise e
        # 不会到这（循环内必 return 或 raise）


class MockModelLayer:
    """模拟模型层：不调 API，纯规则模拟多分类。
    接口与 LLMModelLayer 完全一致，便于开发调试 / 无 key 时兜底。
    """

    def classify(self, text: str) -> dict:
        """按规则模拟多分类。返回结构与真实模型一致。"""
        辱骂词 = ["傻逼", "去死", "滚", "脑残", "智障", "白痴", "畜生", "贱人", "杂种", "狗东西", "煞笔", "废物", "你妈"]
        广告词 = ["加微信", "加v", "vx", "私聊", "私信", "加我", "低价", "优惠", "二维码", "扫码", "链接", "联系我", "领取", "红包", "进群", "公众号"]
        阴阳词 = ["呵呵", "你也配", "就这", "学不来", "高贵", "不配", "有水平", "真是厉害", "哦？", "厉害厉害"]

        if any(w in text for w in 辱骂词):
            return {"分类": "辱骂", "置信度": 0.95, "是否违规": True, "理由": "命中辱骂词"}
        if any(w in text for w in 广告词):
            return {"分类": "广告", "置信度": 0.93, "是否违规": True, "理由": "命中引流词"}
        if any(w in text for w in 阴阳词):
            return {"分类": "阴阳", "置信度": 0.88, "是否违规": True, "理由": "阴阳讽刺语气"}
        return {"分类": "正常", "置信度": 0.90, "是否违规": False, "理由": "无明显违规"}