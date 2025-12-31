from unittest.mock import MagicMock, patch


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
    # collect内で内部関数を呼ぶため、そちらもMock化が必要だが
    # ここでは簡易的に collector.search_by_keywords と collector.get_related_papers をMock化する
    collector = S2Collector()
    collector.search_by_keywords = MagicMock(return_value=[
        {"title": "P1", "year": 2023, "citationCount": 50, "externalIds": {"DOI": "D1"}, "abstract": "A"},
        {"title": "P2", "year": 2020, "citationCount": 5, "externalIds": {"DOI": "D2"}, "abstract": "B"}
    ])
    collector.get_related_papers = MagicMock(return_value=[])

    # min_citations=10, year_range=[2021, 2024]
    df = collector.collect(["test"], [], 10, [2021, 2024])

    assert len(df) == 1
    assert df.iloc[0]["title"] == "P1"
