import logging
import time
from typing import Any

import arxiv
import pandas as pd
import requests
from tenacity import (retry, retry_if_exception, stop_after_attempt,
                      wait_exponential)

from src.utils.constants import APP_LOGGER_NAME

logger = logging.getLogger(f"{APP_LOGGER_NAME}.collector")

S2_API_URL = "https://api.semanticscholar.org/graph/v1"


def is_retryable_s2_error(exception: Exception) -> bool:
    """Semantic Scholar API のリトライ対象エラーかどうかを判定する"""
    if isinstance(exception, requests.exceptions.HTTPError):
        # 429 (Rate Limit) と 5xx (Server Error) をリトライ対象にする
        status_code = exception.response.status_code
        if status_code == 429 or status_code >= 500:
            return True
    return False


class S2Collector:
    def __init__(self):
        self.headers = {}

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=5, max=120),
        retry=retry_if_exception(is_retryable_s2_error),
        before_sleep=lambda retry_state: logger.warning(
            f"Rate limit or server error hit. Retrying in {retry_state.next_action.sleep} seconds... "
            f"(Attempt {retry_state.attempt_number})"
        )
    )
    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{S2_API_URL}/{endpoint}"
        response = requests.get(url, params=params, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def search_by_keywords(self, keywords: list[str], limit: int = 100) -> list[dict[str, Any]]:
        """キーワード検索を実行する"""
        query = " ".join(keywords)
        logger.info(f"Searching papers for keywords: {query}")
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,year,citationCount,abstract,externalIds,url"
        }
        data = self._get("paper/search", params)
        return data.get("data", [])

    def get_related_papers(self, doi: str) -> list[dict[str, Any]]:
        """特定の論文の参考文献と引用文献を取得する"""
        logger.info(f"Getting references and citations for DOI: {doi}")
        params = {
            "fields": "references.title,references.year,references.citationCount,references.abstract,references.externalIds,references.url,"
                      "citations.title,citations.year,citations.citationCount,citations.abstract,citations.externalIds,citations.url"
        }
        try:
            data = self._get(f"paper/DOI:{doi}", params)
            references = data.get("references") or []
            citations = data.get("citations") or []
            related = references + citations
            return related
        except Exception as e:
            logger.error(f"Failed to get related papers for DOI {doi}: {e}")
            return []

    def _fill_missing_abstracts_with_arxiv(self, df: pd.DataFrame) -> pd.DataFrame:
        """抄録が欠けている論文を ArXiv で検索して補完する"""
        missing_mask = df["abstract"].isna() | (df["abstract"] == "")
        missing_count = missing_mask.sum()
        if missing_count == 0:
            return df

        logger.info(f"Attempting to fill missing abstracts for {missing_count} papers using ArXiv API...")

        client = arxiv.Client()

        for idx, row in df[missing_mask].iterrows():
            title = row["title"]
            doi = row.get("doi")

            # DOI または タイトルで検索
            query = f'ti:"{title}"'
            if doi:
                query += f' OR id:{doi}'

            search = arxiv.Search(query=query, max_results=1)
            try:
                # ArXiv API のレートリミットに配慮
                results = list(client.results(search))
                if results:
                    best_match = results[0]
                    # タイトルの類似度チェック（簡易的）
                    if title.lower() in best_match.title.lower() or best_match.title.lower() in title.lower():
                        df.at[idx, "abstract"] = best_match.summary
                        logger.info(f"Filled abstract for: {title}")

                time.sleep(1)  # Rate limit protection

            except Exception as e:
                logger.warning(f"Failed to fetch abstract from ArXiv for {title}: {e}")

        return df

    def collect(self, keywords: list[str], seed_dois: list[str], min_citations: int, year_range: list[int],
                snowball_from_keywords_limit: int = 0) -> pd.DataFrame:
        """全フェーズの収集ロジックを統合する"""
        all_papers = []

        # 1. Keyword Search
        keyword_papers = self.search_by_keywords(keywords)
        all_papers.extend(keyword_papers)

        # 2. Snowballing from specific Seed DOIs
        active_seed_dois = list(seed_dois) if seed_dois else []

        # 3. Add top papers from keyword search to seed DOIs if requested
        if snowball_from_keywords_limit > 0:
            top_keyword_dois = []
            for paper in keyword_papers[:snowball_from_keywords_limit]:
                doi = paper.get("externalIds", {}).get("DOI")
                if doi:
                    top_keyword_dois.append(doi)

            logger.info(f"Adding top {len(top_keyword_dois)} papers from keywords to snowball seeds.")
            active_seed_dois.extend(top_keyword_dois)

        # 4. Citation Mining (Snowballing)
        unique_seeds = list(set(active_seed_dois))
        for doi in unique_seeds:
            related = self.get_related_papers(doi)
            all_papers.extend(related)

        # 5. Deduplication and Initial Filtering
        df = pd.DataFrame(all_papers)
        if df.empty:
            return df

        # 重複排除 (DOI優先、タイトル補助)
        def get_doi(x):
            return x.get("DOI") if isinstance(x, dict) else None

        df["doi"] = df["externalIds"].apply(get_doi)
        df = df.drop_duplicates(subset=["doi"]).drop_duplicates(subset=["title"])

        # 基本フィルタリング
        df = df[df["citationCount"] >= min_citations]
        if len(year_range) == 2:
            df = df[(df["year"] >= year_range[0]) & (df["year"] <= year_range[1])]

        # 6. 抄録の補完 (ArXiv)
        df = self._fill_missing_abstracts_with_arxiv(df)

        logger.info(f"Total papers collected after initial filtering and abstract completion: {len(df)}")
        return df
