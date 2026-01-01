import requests
from unittest.mock import MagicMock, patch

import pytest
import pandas as pd

from src.core.collector import S2Collector, is_retryable_s2_error


@pytest.fixture
def collector():
    return S2Collector()


@patch("src.core.collector.requests.get")
def test_search_by_keywords(mock_get, collector):
    # Mock Response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"title": "Paper 1", "year": 2023, "citationCount": 50, "externalIds": {"DOI": "10.123/1"}},
            {"title": "Paper 2", "year": 2022, "citationCount": 20, "externalIds": {"DOI": "10.123/2"}}
        ]
    }
    mock_get.return_value = mock_response

    results = collector.search_by_keywords(["test"])

    assert len(results) == 2
    assert results[0]["title"] == "Paper 1"
    mock_get.assert_called_once()
    assert mock_get.call_args[1]["params"]["query"] == "test"


def test_collect_filtering(collector):
    # Input papers
    papers = [
        {"title": "P1", "year": 2023, "citationCount": 50, "externalIds": {"DOI": "D1"}, "abstract": "A", "url": "http://p1"},
        {"title": "P2", "year": 2020, "citationCount": 5, "externalIds": {"DOI": "D2"}, "abstract": "B", "url": "http://p2"}
    ]

    # Mocking _fill_missing_abstracts_with_arxiv
    collector._fill_missing_abstracts_with_arxiv = MagicMock(side_effect=lambda df: df)

    # min_citations=10, year_range=[2021, 2024]
    df = collector.process_papers(papers, set(), 10, [2021, 2024])

    assert len(df) == 1
    assert df.iloc[0]["title"] == "P1"


@patch("src.core.collector.S2Collector.get_related_papers")
def test_get_snowball_candidates_threshold(mock_get_related, collector):
    mock_get_related.return_value = [{"title": "Related"}]

    # Create dummy DataFrame with scores
    data = {"doi": [f"10.123/{i}" for i in range(6)], "relevance_score": [10, 9, 8, 7, 6, 5]}
    df = pd.DataFrame(data)

    # Case 1: top_n=2, threshold=None -> Should return 2 (Scores 10, 9)
    collector.get_snowball_candidates(df, top_n=2, threshold=None)
    assert mock_get_related.call_count == 2
    mock_get_related.reset_mock()

    # Case 2: top_n=2, threshold=8 -> Should return 3 (Scores 10, 9, 8)
    collector.get_snowball_candidates(df, top_n=2, threshold=8)
    assert mock_get_related.call_count == 3
    mock_get_related.reset_mock()

    # Case 3: top_n=5, threshold=9 -> Should return 5 (Scores 10, 9, 8, 7, 6)
    collector.get_snowball_candidates(df, top_n=5, threshold=9)
    assert mock_get_related.call_count == 5
    mock_get_related.reset_mock()


@patch("src.core.collector.requests.get")
def test_get_related_papers(mock_get, collector):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "references": [{"title": "Ref1"}],
        "citations": [{"title": "Cit1"}]
    }
    mock_get.return_value = mock_response

    related = collector.get_related_papers("10.123/main")

    assert len(related) == 2
    assert related[0]["title"] == "Ref1"
    assert related[1]["title"] == "Cit1"


@patch("src.core.collector.requests.get")
def test_get_papers_by_dois(mock_get, collector):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"title": "Paper X"}
    mock_get.return_value = mock_response

    results = collector.get_papers_by_dois(["doi1", "doi2"])

    # Should call twice
    assert mock_get.call_count == 2
    assert len(results) == 2


@patch("src.core.collector.S2Collector.search_by_keywords")
@patch("src.core.collector.S2Collector.get_papers_by_dois")
def test_collect_initial(mock_get_dois, mock_search, collector):
    mock_search.return_value = [{"title": "K1"}]
    mock_get_dois.return_value = [{"title": "S1"}]

    results = collector.collect_initial(["kw"], ["doi"])

    assert len(results) == 2
    assert results[0]["title"] == "K1"
    assert results[1]["title"] == "S1"


@patch("src.core.collector.arxiv.Client")
def test_fill_missing_abstracts_with_arxiv(mock_client_cls, collector):
    # Mock arXiv client and search results
    mock_client = mock_client_cls.return_value

    mock_result = MagicMock()
    mock_result.title = "Paper Title"
    mock_result.summary = "ArXiv Abstract"

    # client.results returns a generator/iterator
    mock_client.results.return_value = iter([mock_result])

    # Input DataFrame with missing abstract
    df = pd.DataFrame([
        {"title": "Paper Title", "doi": "10.123/1", "abstract": ""}
    ])

    # Run the method
    # We can patch time.sleep to speed it up
    with patch("src.core.collector.time.sleep"):
        df_filled = collector._fill_missing_abstracts_with_arxiv(df)

    assert df_filled.iloc[0]["abstract"] == "ArXiv Abstract"
    mock_client.results.assert_called()


def test_fill_missing_abstracts_no_op(collector):
    df = pd.DataFrame([
        {"title": "Paper Title", "doi": "10.123/1", "abstract": "Existing Abstract"}
    ])

    # Should return immediately without calling arxiv
    with patch("src.core.collector.arxiv.Client") as mock_client:
        df_filled = collector._fill_missing_abstracts_with_arxiv(df)
        mock_client.assert_not_called()
        assert df_filled.iloc[0]["abstract"] == "Existing Abstract"


def test_is_retryable_s2_error():
    # 429 -> True
    err_429 = requests.exceptions.HTTPError()
    err_429.response = MagicMock(status_code=429)
    assert is_retryable_s2_error(err_429) is True

    # 500 -> True
    err_500 = requests.exceptions.HTTPError()
    err_500.response = MagicMock(status_code=500)
    assert is_retryable_s2_error(err_500) is True

    # 404 -> False
    err_404 = requests.exceptions.HTTPError()
    err_404.response = MagicMock(status_code=404)
    assert is_retryable_s2_error(err_404) is False

    # Other exception -> False
    assert is_retryable_s2_error(ValueError()) is False


@patch("src.core.collector.S2Collector._get")
def test_get_related_papers_edge_cases(mock_get, collector):
    # Exception handling
    mock_get.side_effect = Exception("API Error")
    res = collector.get_related_papers("doi")
    assert res == []

    # Limit logic
    mock_get.side_effect = None
    mock_get.return_value = {
        "references": [{"title": "R1"}, {"title": "R2"}],
        "citations": [{"title": "C1"}]
    }  # Total 3
    res_limit = collector.get_related_papers("doi", limit=2)
    assert len(res_limit) == 2


@patch("src.core.collector.S2Collector._get")
def test_get_papers_by_dois_edge_cases(mock_get, collector):
    # Empty input
    assert collector.get_papers_by_dois([]) == []

    # Exception for one DOI
    mock_get.side_effect = [Exception("Error"), {"title": "Success"}]
    res = collector.get_papers_by_dois(["fail", "success"])
    assert len(res) == 1
    assert res[0]["title"] == "Success"


def test_process_papers_edge_cases(collector):
    # Empty input
    assert collector.process_papers([], set(), 10, [2000, 2025]).empty

    # No DOI field
    papers_no_doi = [{"title": "No DOI", "externalIds": {}}]
    assert collector.process_papers(papers_no_doi, set(), 0, [2000, 2099]).empty

    # Excluded DOI
    papers_excluded = [{"externalIds": {"DOI": "D1"}, "title": "Excluded"}]
    assert collector.process_papers(papers_excluded, {"D1"}, 0, [2000, 2099]).empty

    # Duplicate DOI in same batch
    papers_dup = [
        {"externalIds": {"DOI": "D1"}, "title": "T1", "abstract": "A"},
        {"externalIds": {"DOI": "D1"}, "title": "T1 Duplicate", "abstract": "A"}
    ]
    df_dup = collector.process_papers(papers_dup, set(), 0, [2000, 2099])
    assert len(df_dup) == 1

    # Filter by citations
    papers_cite = [{"externalIds": {"DOI": "D1"}, "citationCount": 5}]
    assert collector.process_papers(papers_cite, set(), 10, [2000, 2099]).empty

    # Filter by year
    papers_year = [{"externalIds": {"DOI": "D1"}, "year": 1999, "citationCount": 100}]
    assert collector.process_papers(papers_year, set(), 0, [2000, 2025]).empty

    # No papers passed criteria
    assert collector.process_papers(papers_cite, set(), 100, [2000, 2025]).empty


def test_get_snowball_candidates_empty(collector):
    assert collector.get_snowball_candidates(pd.DataFrame(), 5) == []


@patch("src.core.collector.logger")
def test_log_retry_attempt(mock_logger):
    from src.core.collector import log_retry_attempt

    # Mock RetryState
    retry_state = MagicMock()
    retry_state.attempt_number = 1
    retry_state.next_action.sleep = 10

    # Case 1: Rate Limit (429)
    err_429 = requests.exceptions.HTTPError()
    err_429.response = MagicMock(status_code=429)
    retry_state.outcome.exception.return_value = err_429

    log_retry_attempt(retry_state)
    mock_logger.warning.assert_called_with(
        "Rate Limit hit. Status Code: 429. Retrying in 10 seconds... (Attempt 1)"
    )

    # Case 2: Server Error (500)
    err_500 = requests.exceptions.HTTPError()
    err_500.response = MagicMock(status_code=500)
    retry_state.outcome.exception.return_value = err_500

    log_retry_attempt(retry_state)
    mock_logger.warning.assert_called_with(
        "Server Error hit. Status Code: 500. Retrying in 10 seconds... (Attempt 1)"
    )

    # Case 3: Other HTTP Error (e.g. 503)
    err_503 = requests.exceptions.HTTPError()
    err_503.response = MagicMock(status_code=503)
    retry_state.outcome.exception.return_value = err_503

    log_retry_attempt(retry_state)
    mock_logger.warning.assert_called_with(
        "Server Error hit. Status Code: 503. Retrying in 10 seconds... (Attempt 1)"
    )

    # Case 4: Non-HTTP Error
    err_other = ValueError("Some error")
    retry_state.outcome.exception.return_value = err_other

    log_retry_attempt(retry_state)
    mock_logger.warning.assert_called_with(
        "Unknown Error hit. Status Code: N/A. Retrying in 10 seconds... (Attempt 1)"
    )
