"""指标引擎：记录每次审核结果，聚合核心指标（漏判率/误判率/介入率/命中分布）。
数据存 JSON，纯本地，无需数据库。可作为平台"可观测、可复盘"的基础。
"""
import json
import time
from pathlib import Path
from collections import Counter, defaultdict


class MetricsEngine:
    def __init__(self, store_path: str = "config/review_records.json"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.records = self._load()

    def _load(self) -> list:
        if self.store_path.exists():
            with open(self.store_path, encoding="utf-8") as f:
                return json.load(f)
        return []

    def save(self) -> None:
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)

    # ===== 记录一次审核结果 =====
    def record(self, result: dict, text: str = "", ground_truth: str | None = None, sampled: bool = False):
        """result: engine.judge 的输出
        ground_truth: 人工真值(可选，"违规"/"正常")
        sampled: 是否被抽检。只有抽检的记录(带真值)才算漏判/误判率。
        """
        rec = {
            "time": int(time.time()),
            "text": text[:50],
            "user_level": result.get("user_level"),
            "action": result.get("action"),
            "source": result.get("source"),
            "detail": result.get("detail", ""),
            "sampled": bool(sampled),
            "ground_truth": ground_truth if sampled else None,   # 非抽检不存真值
        }
        self.records.append(rec)
        self.save()

    # ===== 聚合指标 =====
    def summary(self) -> dict:
        total = len(self.records)
        if total == 0:
            return {"total": 0}

        action_cnt = Counter(r["action"] for r in self.records)
        source_cnt = Counter(r["source"] for r in self.records)
        level_cnt = Counter(r["user_level"] for r in self.records)

        # 命中分布（必杀/打压/观察 的来源）
        命中来源 = Counter()
        for r in self.records:
            if r["source"] == "wordlist":
                detail = r["detail"]
                if "必杀" in detail: 命中来源["必杀"] += 1
                elif "打压" in detail or "降权" in detail: 命中来源["打压"] += 1
                elif "观察" in detail: 命中来源["观察"] += 1
            elif r["source"] == "model":
                命中来源["模型层"] += 1

        # 有真值时漏判/误判率（只在抽检子集上算）
        sampled_records = [r for r in self.records if r["sampled"]]
        judged = [r for r in sampled_records if r["ground_truth"] is not None]
        误判 = [r for r in judged if r["ground_truth"] == "正常" and r["action"] not in ("放行",)]
        漏判 = [r for r in judged if r["ground_truth"] == "违规" and r["action"] == "放行"]
        n = len(judged)

        return {
            "total": total,
            "action分布": dict(action_cnt),
            "来源分布": dict(source_cnt),
            "用户层分布": dict(level_cnt),
            "命中来源": dict(命中来源),
            "人工介入率": round(action_cnt.get("进人工", 0) / total, 3) if total else 0,
            "抽检数": n,
            "抽检率": round(n / total, 3) if total else 0,
            "误判率": round(len(误判) / n, 3) if n else 0,
            "漏判率": round(len(漏判) / n, 3) if n else 0,
        }

    def pretty_summary(self) -> str:
        s = self.summary()
        if s["total"] == 0:
            return "（暂无审核记录）"
        lines = [
            f"总审核量: {s['total']}",
            f"处置分布: {s['action分布']}",
            f"来源分布(词表/模型): {s['来源分布']}",
            f"用户层分布: {s['用户层分布']}",
            f"人工介入率: {s['人工介入率']:.1%}",
            f"抽检数: {s['抽检数']}  误判率: {s['误判率']:.1%}  漏判率: {s['漏判率']:.1%}",
        ]
        return "\n".join(lines)