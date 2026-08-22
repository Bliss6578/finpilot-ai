import json
from pathlib import Path

from app.services.finance_agent import plan_financial_question


def test_financial_agent_evaluation_matrix() -> None:
    cases = json.loads((Path(__file__).parents[1] / "evals" / "financial_agent_cases.json").read_text())
    failures = []
    for case in cases:
        plan = plan_financial_question(case["question"])
        if plan.domain != case["domain"] or plan.intent != case["intent"]:
            failures.append(f"{case['id']}: {plan.domain}/{plan.intent}")
        if case.get("scenario_type") and plan.scenario_type != case["scenario_type"]:
            failures.append(f"{case['id']}: scenario={plan.scenario_type}")
        assert "another client" not in case["question"].casefold() or "authenticated_workspace" not in plan.tools
    assert failures == []
