from app.services.finqa_router import route_reasoning


def test_finqa_router_never_returns_dataset_answers() -> None:
    result = route_reasoning("What percentage of revenue is interest expense?")
    assert result is not None
    assert result["operations"]
    assert result["policy"] == "operation_hint_only"
    assert "answer" not in result
    assert "value" not in result
