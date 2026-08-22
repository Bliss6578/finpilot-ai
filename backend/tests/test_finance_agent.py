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
