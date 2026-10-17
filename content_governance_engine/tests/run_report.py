"""举报治理演示：隔离 / 独立性校验 / 刷量识别 / 处置轻重矩阵。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from review.report import ReportEngine


def main():
    print("=== 举报治理演示 ===\n")

    # ---------- 场景1：单用户举报 → 仅隔离，不复核 ----------
    print("【场景1】单个用户举报一条正常内容")
    e = ReportEngine()
    e.举报({"id": "u1", "ip": "1.1.1.1", "设备": "A", "手机号": "111", "地理": "北京"}, "post_100", 内容是否违规=False)
    print(f"  u1 对 post_100 可见? {e.是否可见('u1','post_100')}  (应为 False=被隔离)")
    print(f"  其他人看 post_100?  {e.是否可见('u2','post_100')}  (应为 True=别人不受影响)")
    print()

    # ---------- 场景2：3个独立用户举报 → 触发复核 ----------
    print("【场景2】3个独立用户举报同一条内容（内容确实违规）")
    e2 = ReportEngine()
    for i, (ip, 设备, 手机, 地理) in enumerate([
        ("2.2.2.2", "B", "222", "上海"),
        ("3.3.3.3", "C", "333", "广州"),
        ("4.4.4.4", "D", "444", "深圳"),
    ], 1):
        d = e2.举报({"id": f"user{i}", "ip": ip, "设备": 设备, "手机号": 手机, "地理": 地理}, "post_200", 内容是否违规=True)
        print(f"  {d['举报者']}: 动作={d['动作']} 独立数={d['独立举报数']} 复核={d['触发复核']}")
    print(f"  最后一条决策: {d.get('复核结论')} → {d.get('后续')}")
    print()

    # ---------- 场景3：同一人重复举报（独立性去重）----------
    print("【场景3】同一用户重复举报同一条（应去重，不触发复核）")
    e3 = ReportEngine()
    for _ in range(5):
        d = e3.举报({"id": "spammer", "ip": "9.9.9.9", "设备": "X", "手机号": "999", "地理": "北京"}, "post_300", False)
    print(f"  同一人举报5次 → 独立数={d['独立举报数']} 复核={d['触发复核']}  (应为 1 / False)")
    print()

    # ---------- 场景4：跨内容刷量 → 限权 ----------
    print("【场景4】一个账号跨内容高频举报（自动化刷量）")
    e4 = ReportEngine(刷量阈值=10)
    result = None
    for i in range(12):
        result = e4.举报({"id": "bot", "ip": f"10.0.0.{i}", "设备": f"dev{i}", "手机号": f"phone{i}", "地理": "北京"}, f"post_{i}")
    print(f"  bot 举报12条不同内容 → 动作={result['动作']} 疑似刷量={result['疑似刷量']}")
    print(f"  说明: {result['说明']}")
    print()

    # ---------- 场景5：处置轻重矩阵 ----------
    print("【场景5】处置轻重矩阵 f(内容是否违规 × 举报是否恶意)")
    e5 = ReportEngine()
    for 内容违规 in (True, False):
        for 恶意 in (True, False):
            r = e5.处置轻重(内容违规, 恶意)
            print(f"  内容违规={str(内容违规):<5} 恶意={str(恶意):<5} → 内容:{r['内容']:<6} 举报者:{r['举报者']:<14} ({r['说明']})")


if __name__ == "__main__":
    main()