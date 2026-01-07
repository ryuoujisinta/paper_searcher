from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.screener import PaperScreener
from src.models.models import ScreeningResult


@pytest.fixture
def screener():
    # Mocking genai.Client in constructor
    with patch("src.core.screener.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        yield PaperScreener("fake_key", "fake_model"), mock_client


def test_screen_papers_success(screener):
    screener_instance, mock_client = screener

    # Mock LLM response
    mock_response = MagicMock()
    mock_response.parsed = ScreeningResult(
        relevance_score=8, relevance_reason="Relevant", summary="Summary"
    )
    mock_client.models.generate_content.return_value = mock_response

    df = pd.DataFrame([{"title": "T1", "abstract": "A1"}])

    result_df = screener_instance.screen_papers(df, "scope")

    assert "relevance_score" in result_df.columns
    assert result_df.iloc[0]["relevance_score"] == 8
    assert result_df.iloc[0]["relevance_reason"] == "Relevant"


def test_screen_papers_no_abstract(screener):
    screener_instance, _ = screener

    df = pd.DataFrame([{"title": "T1", "abstract": ""}])

    result_df = screener_instance.screen_papers(df, "scope")

    assert result_df.iloc[0]["relevance_score"] == 0
    assert result_df.iloc[0]["relevance_reason"] == "No abstract available"


def test_screen_papers_error(screener):
    screener_instance, mock_client = screener

    # Simulate API error
    mock_client.models.generate_content.side_effect = Exception("API Error")

    df = pd.DataFrame([{"title": "T1", "abstract": "A1"}])

    result_df = screener_instance.screen_papers(df, "scope")

    assert result_df.iloc[0]["relevance_score"] == 0
    assert result_df.iloc[0]["relevance_reason"] == "LLM Error occurred"
