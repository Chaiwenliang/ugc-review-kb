"""策略引擎核心：词表×用户分层×模型 → 处置。可配置、可编排、可插拔模型层。"""
from .wordlist import WordlistEngine


# 用户分层（可配置，简化版先用函数，后续可做成配置表）
def 查用户分层(user_profile: dict) -> str:
    if user_profile.get("违规次数", 0) >= 5: return "黑名单"
    if user_profile.get("违规次数", 0) >= 2: return "风险"
    if user_profile.get("违规次数", 0) >= 1: return "灰"
    if user_profile.get("消费额", 0) >= 100: return "白名单"
    return "普通"


class ReviewEngine:
    def __init__(self, wordlist_engine: WordlistEngine, model_layer=None):
        """
        wordlist_engine: 词表引擎（必填）
        model_layer: 模型策略层（可选）。传了就接入语义多分类判断；不传则退回"放行"。
        """
        self.wordlist_engine = wordlist_engine
        self.model_layer = model_layer

    # 核心判定：词表分级 × 用户分层 × 模型
    def judge(self, text: str, user_profile: dict) -> dict:
        user_level = 查用户分层(user_profile)
        wordlist = self.wordlist_engine.get()
        命中的词 = {"必杀": [], "打压": [], "观察": []}

        for 档位 in ["必杀", "打压", "观察"]:
            for 词 in wordlist.get(档位, []):
                if 词 in text:
                    命中的词[档位].append(词)

        # ===== 第1优先级：词表必杀（明确违规，不看用户层，直接拦）=====
        if 命中的词["必杀"]:
            return {"user_level": user_level, "hit": 命中的词, "action": "拦截", "detail": "命中必杀词", "source": "wordlist"}

        # ===== 第2优先级：词表打压（看用户层）=====
        if 命中的词["打压"]:
            if user_level == "白名单": return {"user_level": user_level, "hit": 命中的词, "action": "降权", "detail": "白名单用户降权", "source": "wordlist"}
            if user_level == "黑名单": return {"user_level": user_level, "hit": 命中的词, "action": "拦截", "detail": "黑名单直接拦截", "source": "wordlist"}
            return {"user_level": user_level, "hit": 命中的词, "action": "限流", "detail": "普通/灰限流", "source": "wordlist"}

        # ===== 第3优先级：词表观察 / 未命中 → 交给模型层判语义 =====
        # 模型层接了 → 真的调 LLM 多分类；没接 → 退回"放行"
        if self.model_layer:
            语义 = self.model_layer.classify(text)
            return self._按语义处置(user_level, 命中的词, 语义)
        else:
            if 命中的词["观察"]:
                return {"user_level": user_level, "hit": 命中的词, "action": "放行到模型", "detail": "观察词，但未接模型层", "source": "wordlist"}
            return {"user_level": user_level, "hit": 命中的词, "action": "放行到模型", "detail": "未命中词表，且未接模型层", "source": "wordlist"}

    # 模型语义分类 → 处置
    def _按语义处置(self, user_level: str, 命中的词: dict, 语义: dict) -> dict:
        分类 = 语义.get("分类", "正常")
        置信度 = 语义.get("置信度", 0.0)
        是否违规 = 语义.get("是否违规", 分类 != "正常")
        理由 = 语义.get("理由", "")

        if not 是否违规:
            return {"user_level": user_level, "hit": 命中的词, "action": "放行", "detail": f"模型判正常：{理由}", "source": "model", "model": 语义}

        # 违规：按分类 + 用户层决定处置
        if 分类 == "辱骂":
            if user_level == "白名单": return {"user_level": user_level, "hit": 命中的词, "action": "降权", "detail": f"模型判辱骂（白名单降权）：{理由}", "source": "model", "model": 语义}
            return {"user_level": user_level, "hit": 命中的词, "action": "拦截", "detail": f"模型判辱骂：{理由}", "source": "model", "model": 语义}
        if 分类 == "广告":
            if user_level == "白名单": return {"user_level": user_level, "hit": 命中的词, "action": "降权", "detail": f"模型判广告（白名单降权）：{理由}", "source": "model", "model": 语义}
            return {"user_level": user_level, "hit": 命中的词, "action": "限流", "detail": f"模型判广告：{理由}", "source": "model", "model": 语义}
        if 分类 == "阴阳":
            return {"user_level": user_level, "hit": 命中的词, "action": "降权", "detail": f"模型判阴阳（降权）：{理由}", "source": "model", "model": 语义}

        # 低置信度兜底：进人工
        if 置信度 < 0.6:
            return {"user_level": user_level, "hit": 命中的词, "action": "进人工", "detail": f"低置信度兜底：{理由}", "source": "model", "model": 语义}

        return {"user_level": user_level, "hit": 命中的词, "action": "限流", "detail": f"模型判{分类}：{理由}", "source": "model", "model": 语义}