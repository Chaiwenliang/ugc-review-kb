"""内容治理平台 · Streamlit Web 界面。
整合：词表管理 / 试跑验证 / 指标看板 / 举报治理 / LLM翻译器。
启动：streamlit run app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from review.wordlist import WordlistEngine
from review.engine import ReviewEngine
from review.model_layer import MockModelLayer
from review.metrics import MetricsEngine
from review.report import ReportEngine

# 常量路径
BASE = Path(__file__).parent
词表路径 = BASE / "config" / "wordlist.json"
记录路径 = BASE / "config" / "review_records.json"


@st.cache_resource
def 加载引擎():
    wl = WordlistEngine(词表路径)
    # 优先用真实 LLM 模型层；无 key/失败时回退模拟层
    try:
        from review.model_layer import LLMModelLayer
        ml = LLMModelLayer()
        # 冒烟测试：调一次确认 key 可用
        ml.classify("测试")
        engine = ReviewEngine(wl, ml)
    except Exception:
        from review.model_layer import MockModelLayer
        ml = MockModelLayer()   # 无 key 时用模拟层兜底
        engine = ReviewEngine(wl, ml)
    metrics = MetricsEngine(记录路径)
    return wl, engine, metrics


wl, engine, metrics = 加载引擎()

st.set_page_config(page_title="内容治理平台", layout="wide")
st.title("🛡️ 内容治理平台 · 控制台")

tab1, tab2, tab3, tab4 = st.tabs(["词表管理", "试跑验证", "指标看板", "举报治理"])

# ========== Tab1: 词表管理 ==========
with tab1:
    st.header("词表管理")
    wl_data = wl.get()
    for 档位 in ["必杀", "打压", "观察"]:
        st.subheader(f"{档位}（{len(wl_data.get(档位, []))}词）")
        词s = wl_data.get(档位, [])
        if 词s:
            st.write("、".join(词s))
        else:
            st.write("（空）")

    st.divider()
    st.subheader("增删词")
    档位 = st.selectbox("档位", ["必杀", "打压", "观察"])
    词 = st.text_input("词")
    col1, col2 = st.columns(2)
    if col1.button("➕ 加词") and 词:
        st.write(wl.加词(档位, 词)); wl.save()
    if col2.button("➖ 删词") and 词:
        st.write(wl.删词(档位, 词)); wl.save()

# ========== Tab2: 试跑验证 ==========
with tab2:
    st.header("试跑验证")
    text = st.text_input("输入内容", "加我微信低价出")
    违规 = st.slider("用户历史违规次数", 0, 6, 0)
    if st.button("🚀 判定"):
        profile = {"违规次数": 违规, "消费额": 200 if 违规 == 0 else 0}
        r = engine.judge(text, profile)
        src = "词表" if r["source"] == "wordlist" else "模型"
        st.success(f"**处置: {r['action']}**")
        st.write(f"- 用户层: {r['user_level']}")
        st.write(f"- 来源: {src}")
        st.write(f"- 依据: {r['detail']}")

    st.divider()
    st.subheader("批量示例")
    if st.button("📊 跑 10 条样本并入指标"):
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
        for t, p, truth in 样本:
            metrics.record(engine.judge(t, p), t, ground_truth=truth, sampled=True)
        st.success("已记录并写入指标库")

# ========== Tab3: 指标看板 ==========
with tab3:
    st.header("指标看板")
    s = metrics.summary()
    if s.get("total", 0) == 0:
        st.info("暂无审核记录，请先在『试跑验证』跑一批。")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("总审核量", s["total"])
        c2.metric("人工介入率", f"{s['人工介入率']:.1%}")
        c3.metric("误判率(抽检)", f"{s['误判率']:.1%}")
        c4.metric("漏判率(抽检)", f"{s['漏判率']:.1%}")

        st.subheader("处置分布")
        st.bar_chart(s["action分布"])
        st.subheader("来源分布（词表/模型）")
        st.bar_chart(s["来源分布"])

# ========== Tab4: 举报治理 ==========
with tab4:
    st.header("举报治理演示")
    st.write("按设计：单举报隔离（仅举报人不可见）；3个独立用户举报→触发复核；跨内容高频→限权。")
    if st.button("🎯 模拟 3 个独立用户举报违规内容"):
        rep = ReportEngine()
        d = None
        for i in range(1, 4):
            d = rep.举报({"id": f"u{i}", "ip": f"{i}.1.1.1", "设备": f"D{i}", "手机号": f"222{i}", "地理": "上海"}, "p2", True)
        st.success(f"动作: {d['动作']} | {d['说明']}")
        st.write(f"复核结论: {d.get('复核结论')} → {d.get('后续')}")

    if st.button("🤖 模拟刷量账号（12次高频）"):
        rep2 = ReportEngine()
        r = None
        for i in range(12):
            r = rep2.举报({"id": "bot", "ip": f"10.0.0.{i}", "设备": f"dev{i}", "手机号": f"p{i}", "地理": "北京"}, f"post_{i}")
        st.error(f"动作: {r['动作']} | {r['说明']}")

st.sidebar.info("内容治理平台 · Streamlit 版\n词表管理 / 试跑 / 指标 / 举报 四合一。")