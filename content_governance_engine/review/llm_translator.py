"""LLM 智能翻译器（带澄清追问版）。
走 OpenAI 兼容接口，base_url / model / api_key 均从环境变量读取。
"""
import os
import json
from openai import OpenAI


class LLMTranslator:
    def __init__(self, base_url=None, api_key=None, model=None):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "DeepSeek-V4-Flash-0731")

        if not self.api_key:
            raise ValueError("缺少 API Key：请设置环境变量 LLM_API_KEY 或传入 api_key")

        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def 对话(self, 用户规则, 历史=None):
        历史 = 历史 or []
        system = self._system_prompt()
        messages = [{"role": "system", "content": system}] + 历史 + [{"role": "user", "content": 用户规则}]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)

    def _system_prompt(self):
        return """你是内容治理平台的策略顾问。用户用"人话"描述治理意图，你要把它翻译成结构化的策略配置。

【你的核心任务】
1. 理解用户的治理意图。
2. 判断规则够不够具体、能不能落地。
3. 够具体 → 直接输出策略建议（JSON）。
4. 不够具体 → 用"用户能答得上来"的方式追问，让用户补信息。

【追问铁律 —— 非常重要】
- 绝不能问"置信度阈值是多少""是否排除反讽/谐音""对哪个用户分层生效"这种专业术语。
- 必须用"普通人凭直觉就能答"的话提问。一次最多问 3 个，太多用户会烦。
- 可以这样问：
  · "你能举几个你想拦的具体词或例子吗？比如'傻逼'这种脏话。"
  · "这些是所有人都拦，还是只有经常违规的用户才拦？普通老用户要不要宽容点？"
  · "命中之后，你希望直接删掉、压低曝光，还是只提示一下？"

【可落地标准】一份建议要满足：
- 命中词表：有明确的词或短语
- 用户分层：明确对哪些用户生效
- 处置：明确是 拦截 / 删除 / 降权 / 限流 中的一种

【输出格式（必须JSON）】
- 可落地：{"type": "建议", "建议": {"策略名称": "...", "命中词表": [{"词": "具体词", "处置": "删除/降权/限流/拦截"}, ...], "用户分层": {"档位": "处置"}, "处置": "...", "说明": "..."}}
- 需追问：{"type": "追问", "问题": "...", "问题2": "...", "问题3": "..."}"""


def 交互翻译(translator):
    历史 = []
    print("内容治理顾问已就绪。请用一句话描述你的治理规则。")
    print("（输入 退出 结束）\n")

    while True:
        用户输入 = input("你 > ")
        if 用户输入.strip() in ("退出", "quit", "exit"):
            break

        结果 = translator.对话(用户输入, 历史)
        历史.append({"role": "user", "content": 用户输入})

        if 结果.get("type") == "追问":
            print("\n顾问：")
            for i in range(1, 4):
                q = 结果.get(f"问题{i}") or (结果.get("问题") if i == 1 else None)
                if q:
                    print(f"  {i}. {q}")
            print()
            历史.append({"role": "assistant", "content": json.dumps(结果, ensure_ascii=False)})
        else:
            建议 = 结果.get("建议", {})
            print("\nAI 生成的策略建议：")
            print(json.dumps(建议, ensure_ascii=False, indent=2))
            print("\n这份建议已满足「可落地」条件。")
            # 询问是否落地到引擎试跑
            动作 = input("要不要落地到引擎并试跑验证？(y=落地试跑 / n=跳过 / q=退出) > ").strip().lower()
            if 动作 in ("y", "yes", "落地"):
                落地到引擎(建议)
                历史 = []
                continue
            elif 动作 in ("q", "quit"):
                break
            else:
                print("已跳过落地。可以：继续描述其他规则，或再次输入。\n")
                历史 = []


def 落地到引擎(建议: dict):
    """把 AI 生成的策略建议，写进词表配置，并用引擎跑一遍试跑验证。
    支持两种"命中词表"格式：
      - 字符串数组：["傻逼", "垃圾"]  → 按建议的"处置"统一归档
      - 对象数组：  [{"词":"傻逼","处置":"删除"}, ...] → 每个词单独归档
    """
    from pathlib import Path
    from review.wordlist import WordlistEngine
    from review.engine import ReviewEngine

    # 1. 定位词表配置文件
    config_path = Path(__file__).parent.parent / "config" / "wordlist.json"
    词表 = WordlistEngine(config_path)

    # 2. 解析"命中词表"，得到 (词, 档位) 列表
    命中词表 = 建议.get("命中词表", [])
    默认处置 = 建议.get("处置", "")

    def 处置到档位(处置: str) -> str:
        if 处置 in ("删除", "拦截"):
            return "必杀"
        if 处置 in ("降权", "限流"):
            return "打压"
        return "观察"

    # 智能词型分档：AI 没给每词处置时，按词的类型自动分
    # 硬词（攻击辱骂/明确违规）→ 必杀；软词（广告引流/可能误伤）→ 打压
    def 智能分档(词: str) -> str:
        硬词特征 = ["傻逼", "去死", "滚", "脑残", "智障", "废物", "你妈", "草泥马", "死全家", "煞笔", "贱", "弱智", "白痴", "狗东西", "nmsl", "cnm"]
        软词特征 = ["微信", "加v", "加V", "vx", "VX", "私聊", "私信", "加我", "低价", "优惠", "二维码", "扫码", "链接", "联系我", "领取", "红包", "优惠券", "代购", "刷单"]
        if any(f in 词 for f in 硬词特征):
            return "必杀"
        if any(f in 词 for f in 软词特征):
            return "打压"
        return "必杀"   # 无法判断时，保守用必杀（可人工复核）

    词档对 = []
    for 项 in 命中词表:
        if isinstance(项, dict):          # 对象数组：优先用每词自带的处置
            词 = 项.get("词")
            if not 词:
                continue
            档位 = 处置到档位(项.get("处置", "")) if 项.get("处置") else 智能分档(词)
        else:                              # 字符串数组：用智能分档
            词 = 项
            档位 = 智能分档(词)
        词档对.append((词, 档位))

    # 3. 写进词表（去重，统计各档数量）
    from collections import Counter
    档统计 = Counter()
    for 词, 档位 in 词档对:
        词表.加词(档位, 词)
        档统计[档位] += 1
    词表.save()

    分档说明 = "、".join(f"「{k}」{v}词" for k, v in 档统计.items()) if 档统计 else "无"
    print(f"\n✅ 已写入 {len(词档对)} 个词，分档：{分档说明}，已保存到 config/wordlist.json")

    # 4. 用引擎跑一遍试跑验证
    print("\n--- 试跑验证 ---")
    engine = ReviewEngine(词表)
    测试词 = [w for w, _ in 词档对][:3] or ["测试内容"]
    测试集 = []
    for 词 in 测试词:
        测试集.append((词, {"违规次数": 0, "消费额": 200}))   # 白名单
        测试集.append((词, {"违规次数": 5, "消费额": 0}))    # 黑名单
    测试集.append(("今天天气不错", {"违规次数": 0, "消费额": 0}))  # 正常

    for text, profile in 测试集:
        r = engine.judge(text, profile)
        print(f"  内容:{text!s:<10} 用户层:{r['user_level']:<5} 处置:{r['action']:<6} 依据:{r['detail']}")
    print("\n✅ 落地完成。词表已更新，策略已生效。")