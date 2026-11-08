"""Deterministic game engine for SME FinancePilot (educational simulation only)."""
from copy import deepcopy

STARTING_STATE = {
    "business_name": "Kopi Kita Café",
    "round": 1,
    "cash": 50000.0,
    "revenue": 50000.0,
    "cogs": 18000.0,
    "opex": 22000.0,
    "receivables": 0.0,
    "payables": 0.0,
    "debt": 0.0,
    "cumulative_operating_surplus": 0.0,
    "history": [],
    "decisions": [],
    "score": 0,
    "status": "In progress",
}

EVENTS = {
    1: {
        "title": "The Rising Cost Crisis",
        "category": "COST PRESSURE",
        "story": "Your main supplier has increased ingredient prices. Your cost of goods sold is expected to rise by 15% this month.",
        "learning": "Gross profit = Revenue − COGS. A business can protect its margin through supplier negotiation, cost control or careful pricing.",
        "choices": {
            "A": {"title": "Absorb the increase", "description": "Keep current prices and accept the higher ingredient cost.", "impact": "COGS rises by 15%; sales volume is assumed unchanged."},
            "B": {"title": "Switch supplier", "description": "Use an alternative supplier with a smaller cost increase and a one-off transition cost.", "impact": "COGS rises by 5%; RM800 transition cost; revenue decreases 2% during the switch."},
            "C": {"title": "Adjust selling prices", "description": "Increase menu prices to offset the supplier increase.", "impact": "Revenue rises 6% and COGS rises 15%; demand is assumed unchanged for this demo."},
        },
    },
    2: {
        "title": "The Cash Flow Crisis",
        "category": "LIQUIDITY PRESSURE",
        "story": "A major corporate customer delays RM15,000 of payment. Your supplier and payroll obligations are still due.",
        "learning": "Revenue is recognised when earned, but cash is received later. Delayed collection can create a liquidity problem even when a business is profitable.",
        "choices": {
            "A": {"title": "Negotiate early collection", "description": "Offer a small collection incentive to receive the overdue amount this month.", "impact": "Collect RM15,000 earlier; RM300 collection cost."},
            "B": {"title": "Reschedule supplier payments", "description": "Negotiate to defer RM6,000 of supplier payments to next month.", "impact": "RM6,000 cash payment deferred; it remains a payable."},
            "C": {"title": "Use short-term financing", "description": "Take a simulated RM15,000 short-term facility to bridge the delay.", "impact": "Cash increases RM15,000; debt increases RM15,000; illustrative RM300 interest cost."},
        },
    },
    3: {
        "title": "The Growth Opportunity",
        "category": "INVESTMENT DECISION",
        "story": "A nearby location is available. Opening a second outlet requires RM20,000 in setup investment.",
        "learning": "Growth requires balancing expected return, liquidity, risk and opportunity cost. Capital expenditure affects cash immediately but is not automatically an operating expense.",
        "choices": {
            "A": {"title": "Expand now", "description": "Open the second outlet and commit the setup investment.", "impact": "RM20,000 setup cash outflow; illustrative additional revenue RM12,000, COGS RM4,800 and OPEX RM3,000."},
            "B": {"title": "Preserve cash", "description": "Wait until cash reserves are stronger before expanding.", "impact": "No expansion investment; maintain the current operating model."},
            "C": {"title": "Test a marketing campaign", "description": "Run a smaller campaign before committing to a new outlet.", "impact": "RM2,000 marketing expense; illustrative revenue uplift RM5,000."},
        },
    },
}


def new_game(business_name="Kopi Kita Café", starting_cash=50000.0):
    state = deepcopy(STARTING_STATE)
    state["business_name"] = business_name.strip() or "Kopi Kita Café"
    state["cash"] = float(starting_cash)
    return state


def current_event(state):
    return EVENTS.get(int(state.get("round", 1)))


def financial_snapshot(state):
    revenue = float(state["revenue"])
    cogs = float(state["cogs"])
    opex = float(state["opex"])
    gross_profit = revenue - cogs
    operating_surplus = gross_profit - opex
    return {
        "revenue": round(revenue, 2),
        "cogs": round(cogs, 2),
        "opex": round(opex, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_margin_pct": round(gross_profit / revenue * 100, 2) if revenue else 0.0,
        "operating_surplus": round(operating_surplus, 2),
        "operating_margin_pct": round(operating_surplus / revenue * 100, 2) if revenue else 0.0,
        "cash": round(float(state["cash"]), 2),
        "receivables": round(float(state["receivables"]), 2),
        "payables": round(float(state["payables"]), 2),
        "debt": round(float(state["debt"]), 2),
    }


def _apply_month(state, revenue, cogs, opex, cash_received, cash_paid,
                 capex=0.0, financing_inflow=0.0, new_receivables=0.0,
                 new_payables=0.0, label="Business decision", notes=None):
    opening_cash = float(state["cash"])
    operating_surplus = revenue - cogs - opex
    net_cash_movement = cash_received + financing_inflow - cash_paid - capex
    closing_cash = opening_cash + net_cash_movement
    record = {
        "round": int(state["round"]),
        "label": label,
        "opening_cash": round(opening_cash, 2),
        "revenue": round(revenue, 2),
        "cogs": round(cogs, 2),
        "opex": round(opex, 2),
        "operating_surplus": round(operating_surplus, 2),
        "cash_received": round(cash_received, 2),
        "cash_paid": round(cash_paid, 2),
        "financing_inflow": round(financing_inflow, 2),
        "capex": round(capex, 2),
        "net_cash_movement": round(net_cash_movement, 2),
        "closing_cash": round(closing_cash, 2),
        "notes": notes or [],
    }
    state["cash"] = closing_cash
    state["revenue"] = revenue
    state["cogs"] = cogs
    state["opex"] = opex
    state["receivables"] = max(0.0, float(state["receivables"]) + new_receivables)
    state["payables"] = max(0.0, float(state["payables"]) + new_payables)
    state["cumulative_operating_surplus"] += operating_surplus
    state["history"].append(record)
    state["score"] = calculate_score(state)
    return state


def simulate_decision(state, choice):
    """Apply the selected round action to a copy; caller commits only after owner approval."""
    if state.get("status") == "Completed":
        raise ValueError("This simulation is complete. Start a new game to play again.")
    round_no = int(state["round"])
    if round_no not in EVENTS:
        raise ValueError("No active event. Start a new game.")
    choice = str(choice).upper().strip()
    if choice not in EVENTS[round_no]["choices"]:
        raise ValueError("Please select a valid decision option.")

    s = deepcopy(state)
    rev, cogs, opex = float(s["revenue"]), float(s["cogs"]), float(s["opex"])
    cash_in = rev
    cash_out = cogs + opex
    capex = financing = new_rec = new_pay = 0.0
    notes = []

    if round_no == 1:
        if choice == "A":
            cogs *= 1.15
            notes.append("Supplier price increase absorbed by the business.")
        elif choice == "B":
            cogs *= 1.05
            opex += 800
            rev *= 0.98
            cash_in = rev
            cash_out = cogs + opex
            notes.append("Alternative supplier transition cost included in operating expenses.")
        else:
            cogs *= 1.15
            rev *= 1.06
            cash_in = rev
            cash_out = cogs + opex
            notes.append("Price adjustment assumes sales volume remains unchanged; actual demand may differ.")
    elif round_no == 2:
        delayed = min(15000.0, rev)
        cash_in = rev - delayed
        new_rec = delayed
        if choice == "A":
            cash_in += delayed
            new_rec = 0.0
            opex += 300
            cash_out = cogs + opex
            notes.append("RM15,000 delayed receivable collected early; RM300 collection cost.")
        elif choice == "B":
            deferred = min(6000.0, cogs)
            cash_out = cogs + opex - deferred
            new_pay = deferred
            notes.append(f"RM{deferred:,.0f} supplier payment deferred and carried as payable.")
        else:
            financing = 15000.0
            s["debt"] += financing
            opex += 300
            cash_out = cogs + opex
            notes.append("RM15,000 simulated borrowing; RM300 illustrative interest/financing cost included in OPEX for this simplified game.")
    elif round_no == 3:
        # Round 3 starts with the prior month as the operating baseline.
        if choice == "A":
            rev += 12000
            cogs += 4800
            opex += 3000
            capex = 20000
            cash_in = rev
            cash_out = cogs + opex
            notes.append("Second outlet investment treated as capital expenditure, not operating expense.")
        elif choice == "B":
            cash_in = rev
            cash_out = cogs + opex
            notes.append("Expansion deferred; cash preserved and current operations maintained.")
        else:
            rev += 5000
            opex += 2000
            cash_in = rev
            cash_out = cogs + opex
            notes.append("Marketing spend is treated as operating expense; revenue uplift is illustrative.")

    # Prior deferred supplier payments are settled in the following period unless this round defers again.
    if round_no == 3 and float(s.get("receivables", 0)) > 0:
        collected = float(s["receivables"])
        cash_in += collected
        notes.append(f"Previously delayed customer receivable of RM{collected:,.0f} collected.")
        s["receivables"] = 0.0
    if round_no == 3 and float(s.get("payables", 0)) > 0:
        settlement = float(s["payables"])
        cash_out += settlement
        notes.append(f"Previously deferred supplier payable of RM{settlement:,.0f} settled.")
        s["payables"] = 0.0

    _apply_month(
        s, rev, cogs, opex, cash_in, cash_out,
        capex=capex, financing_inflow=financing,
        new_receivables=new_rec, new_payables=new_pay,
        label=EVENTS[round_no]["choices"][choice]["title"], notes=notes,
    )
    s["decisions"].append({"round": round_no, "choice": choice,
                           "title": EVENTS[round_no]["choices"][choice]["title"]})
    if round_no >= 3:
        s["status"] = "Completed"
    else:
        s["round"] = round_no + 1
    s["score"] = calculate_score(s)
    return s


def calculate_score(state):
    score = 50
    cash = float(state.get("cash", 0))
    surplus = float(state.get("cumulative_operating_surplus", 0))
    debt = float(state.get("debt", 0))
    score += 20 if cash >= 20000 else 10 if cash >= 5000 else 0 if cash >= 0 else -20
    score += 15 if surplus > 0 else -10
    score -= min(20, int(debt / 2000))
    score -= 20 if cash < 0 else 0
    return max(0, min(100, int(score)))


def final_report(state):
    snap = financial_snapshot(state)
    return {
        "business_name": state["business_name"],
        "score": int(state.get("score", 0)),
        "cash": snap["cash"],
        "cumulative_operating_surplus": round(float(state.get("cumulative_operating_surplus", 0)), 2),
        "debt": snap["debt"],
        "receivables": snap["receivables"],
        "payables": snap["payables"],
        "decisions": deepcopy(state.get("decisions", [])),
        "history": deepcopy(state.get("history", [])),
        "status": state.get("status", "In progress"),
    }
