
def spending_risk(monthly_expense, monthly_budget):
    if monthly_budget <= 0:
        return {"risk":"LOW", "usage":0, "remaining":0,
                "explanation":"No monthly budget is set.",
                "suggestion":"Set a monthly budget to monitor spending."}
    usage = (monthly_expense / monthly_budget) * 100
    remaining = monthly_budget - monthly_expense
    if usage < 50:
        risk = "LOW"
        suggestion = "Spending is below half of the budget. Continue tracking regularly."
    elif usage <= 80:
        risk = "MEDIUM"
        suggestion = "Keep an eye on discretionary expenses to stay within budget."
    else:
        risk = "HIGH"
        suggestion = "Review non-essential expenses and consider reducing spending."
    return {"risk":risk, "usage":round(usage,2), "remaining":round(remaining,2),
            "explanation":f"{round(usage,2)}% of the monthly budget has been used.",
            "suggestion":suggestion}
