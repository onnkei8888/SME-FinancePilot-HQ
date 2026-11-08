from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

from game_engine import (EVENTS, current_event, new_game, simulate_decision,
                         financial_snapshot, final_report)
from agent_core import run_agentic_workflow, finance_calculator, cash_flow_calculator, risk_detector, strategy_simulator, DEFAULT_MODEL

st.set_page_config(page_title="SME FinancePilot | Business Survival Simulator", page_icon="🏙️", layout="wide")

# --------------------------- Visual system ---------------------------
st.markdown("""
<style>
:root{--ink:#24364b;--muted:#60758c;--blue:#2563a6;--teal:#24a99a;--green:#42a878;--orange:#f2a65a;--purple:#8973c8}
.stApp{background:#f3f7fb;color:var(--ink)}
[data-testid="stHeader"]{background:rgba(243,247,251,.88)}
h1,h2,h3,h4,p,label,span,div{color:inherit}
[data-testid="stMetric"]{background:#fff;border:1px solid #dce6f0;padding:14px;border-radius:15px;box-shadow:0 3px 12px rgba(40,70,100,.04)}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p{color:#60758c!important}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div{color:#24364b!important;font-weight:800}
[data-testid="stSidebar"]{background:#eaf1f8}
[data-testid="stSidebar"] *{color:#24364b}
.stButton button{border-radius:11px;min-height:43px;font-weight:700;border:1px solid #d2deea;background:#fff;color:#24364b}
.stButton button[kind="primary"]{background:#2563a6;color:white;border:0}
.stButton button:hover{border-color:#24a99a;color:#1c6b70}
[data-testid="stExpander"]{background:#fff;border:1px solid #dce6f0;border-radius:13px}
[data-testid="stTabs"] button{font-weight:700}
.hero{padding:22px 24px;border-radius:20px;background:linear-gradient(115deg,#e3f2fb,#e8f7f2 65%,#fff3e5);border:1px solid #d7e7ef;margin-bottom:16px}
.hero h1{margin:0;color:#193c5a;font-size:30px}.hero p{margin:6px 0 0;color:#526c82}
.panel{background:#fff;border:1px solid #dce6f0;border-radius:16px;padding:17px;margin:8px 0}
.muted{color:#60758c;font-size:13px}.eventtag{display:inline-block;padding:5px 10px;border-radius:99px;background:#fff0d9;color:#8a5a13;font-weight:800;font-size:11px;letter-spacing:.6px}
.good{color:#187b59;font-weight:700}.warn{color:#a46516;font-weight:700}.bad{color:#b33d3d;font-weight:700}
</style>
""", unsafe_allow_html=True)

# --------------------------- Session state ---------------------------
if "game" not in st.session_state:
    st.session_state.game = new_game()
if "agent_result" not in st.session_state:
    st.session_state.agent_result = None
if "last_preview" not in st.session_state:
    st.session_state.last_preview = None
if "owner_approved" not in st.session_state:
    st.session_state.owner_approved = False

state = st.session_state.game
snap = financial_snapshot(state)

# --------------------------- Sidebar ---------------------------
st.sidebar.markdown("# 🏙️ FINANCEPILOT")
st.sidebar.caption("3D SME Business Survival Simulator")
page = st.sidebar.radio("GAME NAVIGATION", [
    "🏠 Business Overview", "🌆 3D Business World", "🎮 Play Simulation",
    "🤖 Finance Core AI", "📊 Financial Intelligence", "🏆 Final Report"
])
st.sidebar.divider()
st.sidebar.markdown("### CURRENT BUSINESS")
st.sidebar.write(f"**{state['business_name']}**")
st.sidebar.caption(f"Round {min(state['round'], 3)} / 3 · {state['status']}")
st.sidebar.metric("Available cash", f"RM {state['cash']:,.0f}")
st.sidebar.metric("Survival score", f"{state['score']} / 100")
st.sidebar.divider()
with st.sidebar.expander("⚙️ Game settings"):
    business_name = st.text_input("Business name", state["business_name"])
    starting_cash = st.number_input("Starting capital (RM)", min_value=5000, max_value=200000, value=50000, step=5000)
    model = st.text_input("Local Ollama model", DEFAULT_MODEL)
    if st.button("Start / reset new game", use_container_width=True):
        st.session_state.game = new_game(business_name, starting_cash)
        st.session_state.agent_result = None
        st.session_state.last_preview = None
        st.session_state.owner_approved = False
        st.rerun()
st.sidebar.caption("DEMO DATA ONLY · No bank connection · No real payments")

# --------------------------- Helpers ---------------------------
def hero(title, subtitle):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)

def metric_row(s):
    a,b,c,d = st.columns(4)
    a.metric("Cash balance", f"RM {s['cash']:,.0f}")
    b.metric("Monthly revenue", f"RM {s['revenue']:,.0f}")
    c.metric("Operating surplus", f"RM {s['operating_surplus']:,.0f}")
    d.metric("Debt", f"RM {s['debt']:,.0f}")

def agent_input_data(s):
    return {
        "revenue": s["revenue"], "cogs": s["cogs"], "opex": s["opex"],
        "opening_cash": s["cash"], "cash_received": max(0, s["revenue"] - s["receivables"]),
        "cash_paid": s["cogs"] + s["opex"] + s["payables"],
        "closing_cash": s["cash"], "financing_inflow": 0, "capex": 0,
        "event_context": current_event(s)["title"] if current_event(s) else "Final review",
        "receivables": s["receivables"], "payables": s["payables"], "debt": s["debt"],
    }

def show_agent_result(result):
    plan = result["plan"]
    st.markdown("#### Finance Core planning")
    st.info(plan.get("goal_interpretation", "Objective understood."))
    st.caption(f"Planner: {plan.get('planner_mode','Unknown')} · {plan.get('reason','')}")
    for i, item in enumerate(plan.get("plan", []), 1):
        st.write(f"**{i}.** {item}")
    st.markdown("#### Dynamic tool selection & execution")
    cols = st.columns(max(1, len(result["outputs"])))
    for col, name in zip(cols, result["outputs"]):
        with col:
            st.markdown(f"<div class='panel'><b>{name.replace('_',' ').title()}</b><br><span class='muted'>{'Executed'}</span></div>", unsafe_allow_html=True)
    for name, output in result["outputs"].items():
        with st.expander(f"Evidence · {name}"):
            st.json(output)
    st.markdown("#### Evaluation & replanning")
    evaluation = result["evaluation"]
    st.write("**Evaluation:** " + ("Sufficient evidence" if evaluation.get("complete") else "Evidence still incomplete"))
    st.caption(evaluation.get("reason", ""))
    if result["replanning"]["attempted"]:
        st.success("Replanning executed. Additional tools: " + ", ".join(result["replanning"]["added_tools"]))
    else:
        st.info("No additional tool call was required by the evaluator for this run.")
    st.markdown("#### Finance Core recommendation & learning coach")
    st.markdown(result["decision"])
    st.caption(result["execution_note"])

# --------------------------- Pages ---------------------------
if page == "🏠 Business Overview":
    hero("Your business. Your decisions. Your future.", "Run a Malaysian SME, navigate financial challenges and learn through consequences.")
    metric_row(snap)
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("### 🧭 Your survival mission")
        if state["status"] == "Completed":
            st.success("All three business rounds completed. Visit Final Report to review your performance.")
        else:
            event = current_event(state)
            st.markdown(f"<div class='panel'><span class='eventtag'>{event['category']}</span><h3>{event['title']}</h3><p>{event['story']}</p><p class='muted'>Round {state['round']} of 3</p></div>", unsafe_allow_html=True)
            if st.button("Continue to current mission →", type="primary", use_container_width=True):
                st.session_state._goto_play = True
                st.rerun()
        st.markdown("### 🏙️ Business world")
        st.caption("Explore the five specialist buildings and the central Finance Core.")
        if st.button("Explore the 3D Business World", use_container_width=True):
            st.session_state._goto_world = True
            st.rerun()
    with right:
        st.markdown("### 📚 What you will learn")
        for icon, title, desc in [
            ("💰", "Profitability", "Revenue, COGS, gross profit and operating surplus."),
            ("💧", "Cash flow", "Actual receipts, payments, receivables and payables."),
            ("🛡️", "Financial risk", "Liquidity pressure, cost ratios and debt."),
            ("🚀", "Growth strategy", "Investment, opportunity cost and risk-return trade-offs."),
        ]:
            st.markdown(f"<div class='panel'><b>{icon} {title}</b><br><span class='muted'>{desc}</span></div>", unsafe_allow_html=True)
    if st.session_state.get("_goto_play"):
        st.session_state._goto_play = False
        st.info("Select **Play Simulation** from the sidebar to continue.")
    if st.session_state.get("_goto_world"):
        st.session_state._goto_world = False
        st.info("Select **3D Business World** from the sidebar to explore.")

elif page == "🌆 3D Business World":
    hero("Isometric SME Business World", "Six interactive landmarks · Five specialist functions · One autonomous Finance Core.")
    html_path = Path(__file__).parent / "components" / "hq_scene.html"
    if html_path.exists():
        components.html(html_path.read_text(encoding="utf-8"), height=680, scrolling=False)
    else:
        st.error("Missing components/hq_scene.html. Keep the components folder beside app.py.")
    st.caption("Tip: click a building in the 3D scene to inspect its role. Drag to rotate and scroll to zoom.")
    st.info("The 3D scene is a visual command centre. Financial calculations and decisions are handled by the Python simulation engine.")

elif page == "🎮 Play Simulation":
    hero("Business Survival Challenge", "Three rounds. Three decisions. One business to keep alive.")
    metric_row(snap)
    if state["status"] == "Completed":
        st.success("Challenge completed! Your final performance is ready.")
        st.balloons()
        st.write("Go to **Final Report** to review your decisions, financial outcomes and learning summary.")
    else:
        event = current_event(state)
        st.markdown(f"<div class='panel'><span class='eventtag'>{event['category']} · ROUND {state['round']}</span><h2>{event['title']}</h2><p>{event['story']}</p></div>", unsafe_allow_html=True)
        st.markdown("### Choose your business strategy")
        choice_labels = {k: f"{k}. {v['title']} — {v['description']}" for k, v in event["choices"].items()}
        selected = st.radio("Your decision", list(choice_labels.keys()), format_func=lambda x: choice_labels[x], key=f"choice_round_{state['round']}")
        st.info("**Expected mechanics:** " + event["choices"][selected]["impact"])
        st.markdown("### Need advice before deciding?")
        advice_col, action_col = st.columns(2)
        with advice_col:
            if st.button("🤖 Ask Finance Core to analyse this event", use_container_width=True):
                goal = f"For round {state['round']} ({event['title']}), assess the current financial position, explain the risks and compare relevant options. Help the owner decide, but do not execute an action."
                with st.spinner("Finance Core is planning, selecting tools and evaluating evidence..."):
                    st.session_state.agent_result = run_agentic_workflow(goal, agent_input_data(state), model.strip() or DEFAULT_MODEL)
                st.rerun()
        with action_col:
            if st.button("✅ Confirm and execute my selected decision", type="primary", use_container_width=True):
                st.session_state.last_preview = simulate_decision(state, selected)
                st.session_state.owner_approved = False
                st.rerun()
        if st.session_state.agent_result:
            with st.expander("Finance Core analysis", expanded=True):
                show_agent_result(st.session_state.agent_result)
        if st.session_state.last_preview is not None:
            preview = st.session_state.last_preview
            st.markdown("### Owner confirmation")
            st.warning("This is a simulated decision only. Review the projected outcome before committing it to the game state.")
            record = preview["history"][-1]
            a,b,c = st.columns(3)
            a.metric("Projected closing cash", f"RM {record['closing_cash']:,.0f}")
            b.metric("Operating surplus", f"RM {record['operating_surplus']:,.0f}")
            c.metric("Net cash movement", f"RM {record['net_cash_movement']:,.0f}")
            st.write("**Decision:** " + record["label"])
            for note in record["notes"]:
                st.caption("• " + note)
            yes,no = st.columns(2)
            with yes:
                if st.button("Approve and update game", type="primary", use_container_width=True):
                    st.session_state.game = preview
                    st.session_state.last_preview = None
                    st.session_state.agent_result = None
                    st.session_state.owner_approved = True
                    st.rerun()
            with no:
                if st.button("Reject and return to decision", use_container_width=True):
                    st.session_state.last_preview = None
                    st.rerun()
        st.markdown("### Learning objective")
        st.write(event["learning"])
    if state.get("history"):
        st.markdown("### Previous rounds")
        st.dataframe(pd.DataFrame(state["history"])[["round", "label", "operating_surplus", "net_cash_movement", "closing_cash"]], use_container_width=True, hide_index=True)

elif page == "🤖 Finance Core AI":
    hero("Finance Core · Autonomous AI Advisor", "Describe a business goal. The agent plans, selects Python tools, evaluates evidence and replans when needed.")
    metric_row(snap)
    goal = st.text_area("Business goal / question", value="Assess my current financial health, identify the most urgent risks and compare practical strategies to protect cash and improve operating surplus.", height=110)
    if st.button("🚀 Run Agentic Workflow", type="primary", use_container_width=True):
        with st.spinner("Finance Core is working locally through Ollama when available..."):
            st.session_state.agent_result = run_agentic_workflow(goal, agent_input_data(state), model.strip() or DEFAULT_MODEL)
    if st.session_state.agent_result:
        show_agent_result(st.session_state.agent_result)
    else:
        st.markdown("#### Try these goals")
        for prompt in ["Can my business pay its obligations? Assess liquidity and cash risk.", "Compare strategies to improve operating surplus.", "Identify the financial impact of the current business event."]:
            st.markdown(f"- {prompt}")
    st.caption("Local Ollama is optional for launching the game. If unavailable, a transparent rule-based fallback keeps the demo usable; the interface labels that fallback clearly.")

elif page == "📊 Financial Intelligence":
    hero("Financial Intelligence", "Understand the difference between profitability, cash movement and financial risk.")
    metric_row(snap)
    fin = finance_calculator({"revenue": state["revenue"], "cogs": state["cogs"], "opex": state["opex"]})
    cash = cash_flow_calculator({"opening_cash": state["cash"], "cash_received": max(0, state["revenue"]-state["receivables"]), "cash_paid": state["cogs"]+state["opex"]+state["payables"]})
    risk = risk_detector({"revenue": state["revenue"], "cogs": state["cogs"], "opex": state["opex"], "closing_cash": state["cash"]})
    t1,t2,t3 = st.tabs(["Profitability", "Cash flow", "Risk"])
    with t1:
        a,b,c = st.columns(3)
        a.metric("Gross profit", f"RM {fin['gross_profit_rm']:,.0f}")
        b.metric("Operating surplus", f"RM {fin['operating_surplus_rm']:,.0f}")
        c.metric("Gross margin", f"{fin['gross_margin_pct']:.1f}%")
        st.caption(fin["definition"])
    with t2:
        a,b,c = st.columns(3)
        a.metric("Cash received", f"RM {cash['cash_received_rm']:,.0f}")
        b.metric("Cash paid", f"RM {cash['cash_paid_rm']:,.0f}")
        c.metric("Estimated closing cash", f"RM {cash['closing_cash_rm']:,.0f}")
        st.caption(cash["method"])
        st.metric("Outstanding receivables", f"RM {state['receivables']:,.0f}")
        st.metric("Outstanding payables", f"RM {state['payables']:,.0f}")
    with t3:
        st.metric("Illustrative risk score", f"{risk['risk_score']} / 100")
        for finding in risk["findings"]:
            if finding["severity"] in ["CRITICAL", "HIGH"]: st.warning(f"{finding['severity']} · {finding['risk']} — {finding['evidence']}")
            else: st.info(f"{finding['severity']} · {finding['risk']} — {finding['evidence']}")
        st.caption(risk["disclaimer"])
    if state["history"]:
        st.markdown("### Financial performance across rounds")
        df = pd.DataFrame(state["history"])
        long = df.melt(id_vars="round", value_vars=["operating_surplus", "net_cash_movement"], var_name="measure", value_name="RM")
        fig = px.bar(long, x="round", y="RM", color="measure", barmode="group", title="Operating surplus vs net cash movement")
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", font_color="#24364b")
        st.plotly_chart(fig, use_container_width=True)

elif page == "🏆 Final Report":
    hero("Business Survival Report", "Your decisions, your financial outcomes and the lessons learned.")
    report = final_report(state)
    a,b,c = st.columns(3)
    a.metric("Survival score", f"{report['score']} / 100")
    b.metric("Final cash", f"RM {report['cash']:,.0f}")
    c.metric("Cumulative operating surplus", f"RM {report['cumulative_operating_surplus']:,.0f}")
    if state["status"] != "Completed":
        st.info(f"You have completed {len(state['decisions'])} of 3 rounds. Complete the remaining missions to unlock the final outcome.")
    else:
        if report["score"] >= 80: st.success("Excellent resilience! You balanced profitability, liquidity and growth decisions.")
        elif report["score"] >= 60: st.info("Good effort. Review your cash buffer and the trade-offs behind your decisions.")
        else: st.warning("Your business faced financial pressure. Review liquidity, costs and financing choices before expanding.")
    st.markdown("### Decision history")
    if report["decisions"]:
        st.dataframe(pd.DataFrame(report["decisions"]), use_container_width=True, hide_index=True)
    if report["history"]:
        st.markdown("### Monthly financial outcomes")
        st.dataframe(pd.DataFrame(report["history"]), use_container_width=True, hide_index=True)
    st.markdown("### Learning reflection")
    st.write("1. **Profitability:** Operating surplus measures revenue less COGS and OPEX in this simplified game; it is not accounting net profit.")
    st.write("2. **Liquidity:** Cash flow depends on when money is actually collected and paid, not only when revenue or expenses are recognised.")
    st.write("3. **Risk:** Borrowing may solve a short-term cash gap but increases debt and future obligations.")
    st.write("4. **Growth:** Expansion uses cash and should be assessed against expected operating returns and the ability to survive downside scenarios.")
    st.download_button("⬇️ Download final report (JSON)", data=json.dumps(report, indent=2), file_name="financepilot_final_report.json", mime="application/json", use_container_width=True)

st.divider()
st.markdown("<div style='text-align:center;color:#71869b;font-size:12px;padding:8px'>SME FinancePilot · Agentic AI Challenge 2026 · Educational simulation · Demo data only</div>", unsafe_allow_html=True)
