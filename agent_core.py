"""Local Ollama agent planner, deterministic tools, evaluator and bounded replanning."""
import json
import urllib.request
import urllib.error
from datetime import datetime

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen3:4b"


def finance_calculator(data):
    revenue, cogs, opex = float(data["revenue"]), float(data["cogs"]), float(data["opex"])
    gross = revenue - cogs
    operating = gross - opex
    return {
        "revenue_rm": round(revenue, 2), "cogs_rm": round(cogs, 2), "opex_rm": round(opex, 2),
        "gross_profit_rm": round(gross, 2),
        "gross_margin_pct": round(gross / revenue * 100, 2) if revenue else 0,
        "operating_surplus_rm": round(operating, 2),
        "operating_margin_pct": round(operating / revenue * 100, 2) if revenue else 0,
        "definition": "Simplified operating surplus = revenue - COGS - operating expenses; it is not accounting net profit.",
    }


def cash_flow_calculator(data):
    opening = float(data["opening_cash"])
    received = float(data["cash_received"])
    paid = float(data["cash_paid"])
    financing = float(data.get("financing_inflow", 0))
    capex = float(data.get("capex", 0))
    movement = received + financing - paid - capex
    return {"opening_cash_rm": round(opening, 2), "cash_received_rm": round(received, 2),
            "cash_paid_rm": round(paid, 2), "financing_inflow_rm": round(financing, 2),
            "capex_rm": round(capex, 2), "net_cash_movement_rm": round(movement, 2),
            "closing_cash_rm": round(opening + movement, 2),
            "method": "Closing cash = opening cash + cash received + financing - cash paid - capital expenditure."}


def risk_detector(data):
    revenue, cogs, opex = float(data["revenue"]), float(data["cogs"]), float(data["opex"])
    closing = float(data.get("closing_cash", data.get("opening_cash", 0)))
    findings, score = [], 0
    if revenue <= 0:
        findings.append({"severity": "CRITICAL", "risk": "No revenue", "evidence": "Revenue is zero or negative."}); score += 45
    if revenue > 0 and cogs / revenue > .55:
        findings.append({"severity": "HIGH", "risk": "High direct-cost ratio", "evidence": f"COGS is {cogs/revenue:.1%} of revenue; prototype threshold is 55%."}); score += 25
    if revenue > 0 and opex / revenue > .40:
        findings.append({"severity": "MEDIUM", "risk": "High operating expense ratio", "evidence": f"OPEX is {opex/revenue:.1%} of revenue; prototype threshold is 40%."}); score += 15
    if closing < 0:
        findings.append({"severity": "CRITICAL", "risk": "Negative closing cash", "evidence": f"Estimated closing cash is RM{closing:,.2f}."}); score += 40
    elif closing < opex:
        findings.append({"severity": "HIGH", "risk": "Low cash buffer", "evidence": f"Closing cash RM{closing:,.2f} is below monthly OPEX RM{opex:,.2f}."}); score += 25
    if not findings:
        findings.append({"severity": "LOW", "risk": "No prototype threshold triggered", "evidence": "No major warning was triggered by the supplied inputs."})
    return {"risk_score": min(score, 100), "findings": findings,
            "disclaimer": "Illustrative rules only; not a credit score or professional risk rating."}


def strategy_simulator(data):
    revenue, cogs, opex = float(data["revenue"]), float(data["cogs"]), float(data["opex"])
    cases = [("Current baseline", 0, 0, 0), ("Cost control", 0, -.05, -.08),
             ("Sales growth", .08, .03, .02), ("Balanced", .04, -.02, -.03)]
    return [{"scenario": n, "revenue_rm": round(revenue*(1+dr), 2),
             "cogs_rm": round(cogs*(1+dc), 2), "opex_rm": round(opex*(1+do), 2),
             "operating_surplus_rm": round(revenue*(1+dr)-cogs*(1+dc)-opex*(1+do), 2),
             "assumption": "Illustrative sensitivity assumption, not a forecast."} for n, dr, dc, do in cases]


def event_impact_simulator(data):
    event = data.get("event_context", "General operating pressure")
    revenue, cogs, opex = float(data["revenue"]), float(data["cogs"]), float(data["opex"])
    return {"event_context": event, "baseline_operating_surplus_rm": round(revenue-cogs-opex, 2),
            "supplier_cost_plus_15pct_surplus_rm": round(revenue-cogs*1.15-opex, 2),
            "receivable_delay_cash_effect_rm": -15000.0,
            "note": "Scenario mechanics are illustrative. Use actual assumptions before making a real business decision."}


TOOLS = {
    "finance_calculator": {"role": "Finance Specialist", "description": "Calculate gross profit, operating surplus and margins.", "fn": finance_calculator},
    "cash_flow_calculator": {"role": "Cash Flow Specialist", "description": "Calculate net cash movement and estimated closing cash.", "fn": cash_flow_calculator},
    "risk_detector": {"role": "Risk Specialist", "description": "Identify high cost ratios, low cash buffer and negative cash.", "fn": risk_detector},
    "strategy_simulator": {"role": "Strategy Specialist", "description": "Compare four illustrative operating scenarios.", "fn": strategy_simulator},
    "event_impact_simulator": {"role": "Event Analyst", "description": "Quantify selected illustrative business-event impacts.", "fn": event_impact_simulator},
}


def _ollama(messages, model, json_mode=False, timeout=120):
    body = {"model": model, "messages": messages, "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 8192}}
    if json_mode:
        body["format"] = "json"
    request = urllib.request.Request(OLLAMA_CHAT_URL, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))["message"]["content"]
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Ollama unavailable or returned an invalid response: {exc}") from exc


def _parse_json(raw):
    raw = raw.strip().replace("```json", "").replace("```", "")
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("The model did not return a valid JSON object.")
    return json.loads(raw[start:end+1])


def _fallback_plan(goal, data):
    text = goal.lower()
    selected = []
    if any(k in text for k in ["cash", "liquidity", "pay", "runway", "collect"]):
        selected.append("cash_flow_calculator")
    if any(k in text for k in ["risk", "safe", "danger", "crisis", "survive"]):
        selected.append("risk_detector")
    if any(k in text for k in ["strategy", "compare", "option", "improve", "expand", "growth"]):
        selected.append("strategy_simulator")
    if any(k in text for k in ["event", "supplier", "delay", "impact"]):
        selected.append("event_impact_simulator")
    if any(k in text for k in ["profit", "financial", "margin", "cost", "business"]):
        selected.append("finance_calculator")
    if not selected:
        selected = ["finance_calculator", "cash_flow_calculator", "risk_detector"]
    selected = list(dict.fromkeys(selected))[:4]
    return {"goal_interpretation": "Identify the financial analysis needed to answer the owner's objective.",
            "plan": [f"Run {TOOLS[name]['role']} analysis" for name in selected],
            "selected_tools": selected,
            "reason": "Local rule-based fallback used because Ollama was unavailable. This is not an LLM-generated plan."}


def _make_plan(goal, data, model, previous=None):
    catalog = "\n".join(f"{name}: {item['description']}" for name, item in TOOLS.items())
    system = ("You are Finance Core, a careful planner for a simulated Malaysian SME. "
              "Select the minimum relevant tools from this allow-list only:\n" + catalog +
              "\nReturn JSON with keys goal_interpretation, plan (array), selected_tools (array), reason. "
              "Never invent tool names. Select 1 to 4 tools. Calculations must come from tools.")
    user = f"Owner goal: {goal}\nBusiness state: {json.dumps(data)}\nPrevious results (if any): {json.dumps(previous or {})}"
    try:
        result = _parse_json(_ollama([{"role": "system", "content": system},
                                      {"role": "user", "content": user}], model, True))
        chosen = [name for name in result.get("selected_tools", []) if name in TOOLS]
        if not chosen:
            raise ValueError("Planner did not select an allowed tool.")
        result["selected_tools"] = list(dict.fromkeys(chosen))[:4]
        result["planner_mode"] = "Ollama LLM"
        return result
    except Exception as exc:
        fallback = _fallback_plan(goal, data)
        fallback["planner_mode"] = "Rule-based fallback"
        fallback["fallback_reason"] = str(exc)
        return fallback


def _evaluate(goal, outputs, model):
    if not outputs:
        return {"complete": False, "missing": ["No tools were executed"], "reason": "No evidence available."}
    system = ("You evaluate whether tool results adequately answer a business owner's goal. "
              "Return JSON only: {complete:boolean, missing:[string], reason:string, additional_tools:[allowed tool names]}. "
              "Only request tools from the supplied allow-list. Do not request more than two additional tools.")
    user = f"Goal: {goal}\nExecuted tool results: {json.dumps(outputs)}\nAllowed tools: {list(TOOLS)}"
    try:
        result = _parse_json(_ollama([{"role": "system", "content": system},
                                      {"role": "user", "content": user}], model, True))
        additional = [n for n in result.get("additional_tools", []) if n in TOOLS]
        result["additional_tools"] = list(dict.fromkeys(additional))[:2]
        result["evaluator_mode"] = "Ollama LLM"
        return result
    except Exception as exc:
        # Deterministic completeness check ensures a bounded evaluation step even offline.
        needs_cash = any(k in goal.lower() for k in ["cash", "liquidity", "pay", "runway"])
        missing = needs_cash and "cash_flow_calculator" not in outputs
        return {"complete": not missing, "missing": ["Cash-flow evidence is needed for this goal."] if missing else [],
                "reason": "Offline evaluator checked whether a cash objective has cash-flow evidence.",
                "additional_tools": ["cash_flow_calculator"] if missing else [],
                "evaluator_mode": "Rule-based fallback", "fallback_reason": str(exc)}


def _decision(goal, data, outputs, model):
    system = ("You are the SME FinancePilot learning coach. Use only supplied data and tool outputs. "
              "Never invent numbers or claim a real transaction occurred. Clearly distinguish operating surplus "
              "from cash flow and accounting net profit. Explain risks, assumptions and one practical next step. "
              "Keep the answer concise and understandable to a beginner.")
    user = f"Owner goal: {goal}\nInputs: {json.dumps(data)}\nTool evidence: {json.dumps(outputs)}"
    try:
        return _ollama([{"role": "system", "content": system}, {"role": "user", "content": user}], model, False)
    except Exception:
        parts = ["### Finance Core analysis (offline fallback)", f"**Objective:** {goal}"]
        for name, output in outputs.items():
            parts.append(f"**{TOOLS[name]['role']} — {name}:**\n```json\n{json.dumps(output, indent=2)}\n```")
        parts.append("**Learning point:** Operating surplus is based on earned revenue and operating costs; cash flow tracks actual cash received and paid. Neither figure alone should be labelled accounting net profit.")
        parts.append("**Next step:** Verify payment timing, supplier terms and all scenario assumptions before approving a simulated action.")
        return "\n\n".join(parts)


def run_agentic_workflow(goal, data, model=DEFAULT_MODEL):
    """Plan -> execute tools -> evaluate -> one bounded replan -> synthesize."""
    plan = _make_plan(goal, data, model)
    selected = plan["selected_tools"]
    outputs = {name: TOOLS[name]["fn"](data) for name in selected}
    evaluation = _evaluate(goal, outputs, model)
    replanning = {"attempted": False, "added_tools": []}
    if not evaluation.get("complete", False):
        extra = [n for n in evaluation.get("additional_tools", []) if n not in outputs][:2]
        if extra:
            replanning["attempted"] = True
            replanning["added_tools"] = extra
            # Explicitly bounded: one additional execution pass only.
            for name in extra:
                outputs[name] = TOOLS[name]["fn"](data)
            evaluation = _evaluate(goal, outputs, model)
    decision = _decision(goal, data, outputs, model)
    return {"goal": goal, "plan": plan, "selected_tools": selected,
            "outputs": outputs, "evaluation": evaluation, "replanning": replanning,
            "decision": decision, "timestamp": datetime.now().strftime("%d %b %Y %H:%M:%S"),
            "execution_note": "Python tools perform deterministic calculations. Ollama plans/evaluates when available; transparent rule-based fallback is used otherwise."}
