from app.services.finance_agent import is_financial_question, plan_financial_question


def test_native_agent_rejects_unrelated_questions() -> None:
    assert is_financial_question("How much runway do I have?") is True
    assert is_financial_question("Write a birthday poem") is False


def test_native_agent_plans_workspace_tools_and_extracts_scenario() -> None:
    plan = plan_financial_question(
        "Can I hire 2 people at ₹50,000 per month and still protect my reserve for 90 days?"
    )

    assert plan.intent == "decision_scenario"
    assert plan.period_days == 90
    assert "simulate_scenario" in plan.tools
    assert plan.scenario_type == "new_hire"
    assert plan.scenario_parameters == {
        "employees": 2.0,
        "monthly_salary_paise": 5_000_000.0,
    }


def test_native_agent_extracts_each_supported_decision_scenario() -> None:
    marketing = plan_financial_question("What if I spend ₹25,000 per month on marketing?")
    assert marketing.scenario_type == "marketing"
    assert marketing.scenario_parameters == {"monthly_budget_paise": 2_500_000.0}
    revenue = plan_financial_question("What if sales fall by 12%?")
    assert revenue.scenario_parameters == {"revenue_change_percent": -12.0}
    expenses = plan_financial_question("What if I cut costs by 8%?")
    assert expenses.scenario_parameters == {"expense_change_percent": 8.0}
    purchase = plan_financial_question("Can I afford to buy equipment for ₹2 lakh?")
    assert purchase.scenario_type == "one_time_purchase"
    assert purchase.scenario_parameters == {"one_time_paise": 20_000_000.0}


def test_native_agent_combines_multiple_assumptions() -> None:
    plan = plan_financial_question(
        "Hire 2 people at ₹50,000 per month, increase marketing by ₹20,000, "
        "let revenue fall 10%, cut expenses by 5%, and buy equipment for ₹1 lakh"
    )
    assert plan.scenario_type == "custom"
    assert plan.scenario_parameters == {
        "monthly_cost_paise": 12_000_000.0,
        "employees": 2.0,
        "monthly_salary_paise": 5_000_000.0,
        "monthly_budget_paise": 2_000_000.0,
        "revenue_change_percent": -10.0,
        "expense_change_percent": -5.0,
        "one_time_paise": 10_000_000.0,
    }
