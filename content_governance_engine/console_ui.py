"""内容治理平台 · 控制台界面（零依赖，纯Python）。
整合：词表管理 / 试跑验证 / 指标看板 / 举报治理 / 开发脑图。
作为平台的"操作入口"，可交互操作。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from review.wordlist import WordlistEngine
from review.engine import ReviewEngine
from review.model_layer import MockModelLayer
from review.metrics import MetricsEngine
from review.report import ReportEngine


词表路径 = Path(__file__).parent / "config" / "wordlist.json"
记录路径 = Path(__file__).parent / "config" / "review_records.json"


def 加载组件():
    wl = WordlistEngine(词表路径)
    ml = MockModelLayer()
    engine = ReviewEngine(wl, ml)
    metrics = MetricsEngine(记录路径)
    report = ReportEngine()
    return wl, ml, engine, metrics, report


def 打印词表(wl):
    print("\n===== 当前词表 =====")
    wl_data = wl.get()
    for 档位 in ["必杀", "打压", "观察"]:
        词s = wl_data.get(档位, [])
        print(f"  [{档位}] ({len(词s)}词): {', '.join(词s[:12])}{'...' if len(词s)>12 else ''}")
    print(f"  版本: {wl_data.get('version')}")


def 菜单():
    加载 = None
    print("\n" + "=" * 46)
    print("  内容治理平台 · 控制台")
    print("=" * 46)
    while True:
        print("\n请选择操作:")
        print("  1. 查看/管理词表")
        print("  2. 单条试跑验证")
        print("  3. 批量跑 + 指标看板")
        print("  4. 举报治理演示")
        print("  5. 退出")
        选择 = input("> ").strip()

        if 选择 == "1":
            if 加载 is None: 加载 = 加载组件()
            wl = 加载[0]
            打印词表(wl)
            动作 = input("  (a)加词 (b)删词 (c)返回 > ").strip().lower()
            if 动作 in ("a", "加词"):
                档位 = input("  档位(必杀/打压/观察)> ").strip()
                词 = input("  词> ").strip()
                print("  " + wl.加词(档位, 词)); wl.save()
            elif 动作 in ("b", "删词"):
                档位 = input("  档位> ").strip(); 词 = input("  词> ").strip()
                print("  " + wl.删词(档位, 词)); wl.save()

        elif 选择 == "2":
            if 加载 is None: 加载 = 加载组件()
            engine = 加载[2]
            text = input("  输入内容> ").strip()
            违规 = input("  违规次数(默认0)> ").strip() or "0"
            profile = {"违规次数": int(违规), "消费额": 0}
            r = engine.judge(text, profile)
            src = "词表" if r["source"] == "wordlist" else "模型"
            print(f"  → 用户层:{r['user_level']} 处置:{r['action']} 来源:{src}")
            print(f"    依据:{r['detail']}")

        elif 选择 == "3":
            if 加载 is None: 加载 = 加载组件()
            engine, metrics = 加载[2], 加载[3]
            print("  用内置样本跑10条并聚合指标...")
            样本 = [
                ("加我微信", {"违规次数":0,"消费额":200}, "违规"),
                ("你这个傻逼", {"违规次数":0,"消费额":500}, "违规"),
                ("今天天气不错", {"违规次数":0,"消费额":0}, "正常"),
                ("呵呵就你也配", {"违规次数":0,"消费额":0}, "违规"),
                ("加我微信", {"违规次数":2,"消费额":0}, "违规"),
                ("好货低价出", {"违规次数":0,"消费额":0}, "违规"),
                ("真心感谢帮忙", {"违规次数":0,"消费额":0}, "正常"),
                ("你妈", {"违规次数":1,"消费额":0}, "违规"),
                ("加V", {"违规次数":0,"消费额":0}, "违规"),
                ("正常交流", {"违规次数":0,"消费额":0}, "正常"),
            ]
            for text, profile, truth in 样本:
                metrics.record(engine.judge(text, profile), text, ground_truth=truth, sampled=True)
            print("\n" + metrics.pretty_summary())

        elif 选择 == "4":
            if 加载 is None: 加载 = 加载组件()
            report = 加载[4]
            print("  举报治理：单举报隔离 / 3独立触发复核 / 刷量识别")
            r = report.举报({"id":"u1","ip":"1.1.1.1","设备":"A","手机号":"111","地理":"北京"}, "p1", False)
            print(f"  [单举报] {r['动作']} — {r['说明']}")
            e2 = ReportEngine()
            for i in range(1,4):
                d = e2.举报({"id":f"u{i}","ip":f"{i}.1.1.1","设备":f"D{i}","手机号":f"222{i}","地理":"上海"}, "p2", True)
            print(f"  [多独立] {d['动作']} — {d['说明']} → {d.get('复核结论')}")

        elif 选择 == "5":
            print("  已退出。"); break
        else:
            print("  无效选择")


if __name__ == "__main__":
    菜单()