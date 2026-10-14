"""策略引擎核心：词表×用户分层×模型 → 处置。可配置、可编排、可插拔模型层。

动态用户分层处置：
- 不再只看"这一条"，而是结合"用户历史违规次数"决定力度。
- 首犯从轻（提醒）、轻微降权、屡犯从严（删除/拦截）。
- 白名单/高消费老用户更宽容。
"""
from .wordlist import WordlistEngine


# 用户分层（按画像算档位）
def 查用户分层(user_profile: dict) -> str:
    if user_profile.get("违规次数", 0) >= 5: return "黑名单"
    if user_profile.get("违规次数", 0) >= 2: return "风险"
    if user_profile.get("违规次数", 0) >= 1: return "灰"
    if user_profile.get("消费额", 0) >= 100: return "白名单"
    return "普通"


class ReviewEngine:
    def __init__(self, wordlist_engine: WordlistEngine, model_layer=None):
        self.wordlist_engine = wordlist_engine
        self.model_layer = model_layer

    # ===== 核心判定 =====
    def judge(self, text: str, user_profile: dict) -> dict:
        user_level = 查用户分层(user_profile)
        wordlist = self.wordlist_engine.get()
        命中的词 = {"必杀": [], "打压": [], "观察": []}

        for 档位 in ["必杀", "打压", "观察"]:
            for 词 in wordlist.get(档位, []):
                if 词 in text:
                    命中的词[档位].append(词)

        # 是否老用户/高信任（白名单）→ 宽容
        是老用户 = (user_level == "白名单")

        # ===== 第1优先级：词表必杀 =====
        # 明确违规（攻击辱骂硬词）→ 直接拦。但老用户首次可降为降权？
        # 设计：必杀词 = 底线违规，不看违规次数直接拦；老用户也拦（这是红线）
        if 命中的词["必杀"]:
            return {"user_level": user_level, "hit": 命中的词, "action": "拦截", "detail": "命中必杀词（红线，直接拦）", "source": "wordlist"}

        # ===== 第2优先级：词表打压 =====
        # 打压词（广告/引流等）→ 按"用户历史违规次数"动态处置
        if 命中的词["打压"]:
            return self._动态处置(user_level, 命中的词, "打压", 是老用户)

        # ===== 第3优先级：观察 / 未命中 → 模型层 =====
        if self.model_layer:
            语义 = self.model_layer.classify(text)
            return self._按语义处置(user_level, 命中的词, 语义)
        else:
            if 命中的词["观察"]:
                return {"user_level": user_level, "hit": 命中的词, "action": "放行到模型", "detail": "观察词，但未接模型层", "source": "wordlist"}
            return {"user_level": user_level, "hit": 命中的词, "action": "放行到模型", "detail": "未命中词表，且未接模型层", "source": "wordlist"}

    # ===== 动态处置：结合违规次数 + 是否老用户 =====
    def _动态处置(self, user_level: str, 命中的词: dict, 档位: str, 是老用户: bool) -> dict:
        # 从命中记录里取一个代表词（用于 detail）
        代表词 = 命中的词[档位][0] if 命中的词[档位] else ""
        # 违规次数 = 这次命中前的历史违规次数 + 1（本次）
        历史违规 = 命中的词.get("_违规次数", 0)
        # 这里简化：从 user_profile 不好取，用档位优先级推断
        # 白名单老用户 → 从轻
        if 是老用户:
            return {"user_level": user_level, "hit": 命中的词, "action": "降权", "detail": f"老用户命中[{代表词}]→从轻降权", "source": "wordlist"}
        # 黑名单 → 从严
        if user_level == "黑名单":
            return {"user_level": user_level, "hit": 命中的词, "action": "拦截", "detail": f"黑名单命中[{代表词}]→直接拦截", "source": "wordlist"}
        # 风险用户 → 从严
        if user_level == "风险":
            return {"user_level": user_level, "hit": 命中的词, "action": "拦截", "detail": f"风险用户命中[{代表词}]→从严拦截", "source": "wordlist"}
        # 灰用户 → 限流
        if user_level == "灰":
            return {"user_level": user_level, "hit": 命中的词, "action": "限流", "detail": f"灰用户命中[{代表词}]→限流", "source": "wordlist"}
        # 普通用户 → 首犯提醒 / 轻微限流
        return {"user_level": user_level, "hit": 命中的词, "action": "限流", "detail": f"普通用户命中[{代表词}]→限流观察", "source": "wordlist"}

    # ===== 模型语义分类 → 处置 =====
    def _按语义处置(self, user_level: str, 命中的词: dict, 语义: dict) -> dict:
        分类 = 语义.get("分类", "正常")
        置信度 = 语义.get("置信度", 0.0)
        是否违规 = 语义.get("是否违规", 分类 != "正常")
        理由 = 语义.get("理由", "")

        if not 是否违规:
            return {"user_level": user_level, "hit": 命中的词, "action": "放行", "detail": f"模型判正常：{理由}", "source": "model", "model": 语义}

        # 违规：按分类 + 用户层
        if 分类 == "辱骂":
            if user_level == "白名单": return {"user_level": user_level, "hit": 命中的词, "action": "降权", "detail": f"模型判辱骂（白名单降权）：{理由}", "source": "model", "model": 语义}
            return {"user_level": user_level, "hit": 命中的词, "action": "拦截", "detail": f"模型判辱骂：{理由}", "source": "model", "model": 语义}
        if 分类 == "广告":
            if user_level == "白名单": return {"user_level": user_level, "hit": 命中的词, "action": "降权", "detail": f"模型判广告（白名单降权）：{理由}", "source": "model", "model": 语义}
            return {"user_level": user_level, "hit": 命中的词, "action": "限流", "detail": f"模型判广告：{理由}", "source": "model", "model": 语义}
        if 分类 == "阴阳":
            return {"user_level": user_level, "hit": 命中的词, "action": "降权", "detail": f"模型判阴阳（降权）：{理由}", "source": "model", "model": 语义}

        if 置信度 < 0.6:
            return {"user_level": user_level, "hit": 命中的词, "action": "进人工", "detail": f"低置信度兜底：{理由}", "source": "model", "model": 语义}

        return {"user_level": user_level, "hit": 命中的词, "action": "限流", "detail": f"模型判{分类}：{理由}", "source": "model", "model": 语义}