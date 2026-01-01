from unittest.mock import MagicMock, patch
import pandas as pd


from src.core.collector import S2Collector


@patch("src.core.collector.requests.get")
def test_search_by_keywords(mock_get):
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

    collector = S2Collector()
    results = collector.search_by_keywords(["test"])

    assert len(results) == 2
    assert results[0]["title"] == "Paper 1"
    mock_get.assert_called_once()


def test_collect_filtering():
    collector = S2Collector()

    # Input papers
    papers = [
        {"title": "P1", "year": 2023, "citationCount": 50, "externalIds": {"DOI": "D1"}, "abstract": "A", "url": "http://p1"},
        {"title": "P2", "year": 2020, "citationCount": 5, "externalIds": {"DOI": "D2"}, "abstract": "B", "url": "http://p2"}
    ]

    # Mocking _fill_missing_abstracts_with_arxiv since it makes external calls
    collector._fill_missing_abstracts_with_arxiv = MagicMock(side_effect=lambda df: df)

    # min_citations=10, year_range=[2021, 2024]
    # process_papers expects a list of dicts as input
    df = collector.process_papers(papers, set(), 10, [2021, 2024])

    assert len(df) == 1
    assert df.iloc[0]["title"] == "P1"


@patch("src.core.collector.S2Collector.get_related_papers")
def test_get_snowball_candidates_threshold(mock_get_related):
    collector = S2Collector()
    mock_get_related.return_value = [{"title": "Related"}]

    # Create dummy DataFrame with scores
    # Scores: 10, 9, 8, 7, 6, 5
    data = {"doi": [f"10.123/{i}" for i in range(6)], "relevance_score": [10, 9, 8, 7, 6, 5]}
    df = pd.DataFrame(data)

    # Case 1: top_n=2, threshold=None -> Should return 2 (Scores 10, 9)
    collector.get_snowball_candidates(df, top_n=2, threshold=None)
    assert mock_get_related.call_count == 2
    mock_get_related.reset_mock()

    # Case 2: top_n=2, threshold=8 -> Should return 3 (Scores 10, 9, 8)
    # Because count(>=8) is 3, which is > top_n(2)
    collector.get_snowball_candidates(df, top_n=2, threshold=8)
    assert mock_get_related.call_count == 3
    mock_get_related.reset_mock()

    # Case 3: top_n=5, threshold=9 -> Should return 5 (Scores 10, 9, 8, 7, 6)
    # Because count(>=9) is 2, which is < top_n(5). So max is 5.
    collector.get_snowball_candidates(df, top_n=5, threshold=9)
    assert mock_get_related.call_count == 5
    mock_get_related.reset_mock()
