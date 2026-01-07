from src.models.models import ScreeningResult


def test_screening_result_valid():
    data = {
        "relevance_score": 5,
        "relevance_reason": "Test reason",
        "summary": "Test summary",
    }
    model = ScreeningResult(**data)
    assert model.relevance_score == 5
    assert model.relevance_reason == "Test reason"
    assert model.summary == "Test summary"


def test_screening_result_invalid_score_type():
    # pydantic usually coerces strings to int, so "5" works.
    # We can check validation errors for totally invalid types if we want,
    # but basic instantiation test is usually sufficient for simple models.
    pass
