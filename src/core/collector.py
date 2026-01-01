import logging
import time
from typing import Any

import arxiv
import pandas as pd
import requests
from tenacity import (retry, retry_if_exception, stop_after_attempt,
                      wait_exponential)
from tqdm import tqdm

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

    def get_related_papers(self, doi: str, limit: int = -1) -> list[dict[str, Any]]:
        """特定の論文の参考文献と引用文献を取得する"""
        logger.info(f"Getting references and citations for DOI: {doi} (Limit: {limit})")
        params = {
            "fields": "references.title,references.year,references.citationCount,references.abstract,references.externalIds,references.url,"
                      "citations.title,citations.year,citations.citationCount,citations.abstract,citations.externalIds,citations.url"
        }
        try:
            data = self._get(f"paper/DOI:{doi}", params)
            references = data.get("references") or []
            citations = data.get("citations") or []
            related = references + citations

            if limit != -1 and len(related) > limit:
                logger.info(f"Limiting related papers from {len(related)} to {limit}")
                related = related[:limit]

            return related
        except Exception as e:
            logger.error(f"Failed to get related papers for DOI {doi}: {e}")
            return []

    def get_papers_by_dois(self, dois: list[str]) -> list[dict[str, Any]]:
        """複数のDOIから論文情報を一括取得する"""
        if not dois:
            return []

        logger.info(f"Fetching details for {len(dois)} DOIs")
        results = []
        # Semantic Scholar API might have limits on batch size, but we'll do one by one for simplicity
        # or use batch API if available. For now, one by one is safer for rate limits with our retry logic.
        for doi in dois:
            try:
                params = {"fields": "title,year,citationCount,abstract,externalIds,url"}
                data = self._get(f"paper/DOI:{doi}", params)
                if data:
                    results.append(data)
            except Exception as e:
                logger.warning(f"Failed to fetch paper for DOI {doi}: {e}")
        return results

    def collect_initial(self, keywords: list[str], seed_dois: list[str], limit: int = 100) -> list[dict[str, Any]]:
        """初期収集: キーワード検索とSeed DOIからの取得をマージする"""
        all_candidates = []

        # 1. Keyword Search
        if keywords:
            keyword_papers = self.search_by_keywords(keywords, limit=limit)
            all_candidates.extend(keyword_papers)
            logger.info(f"Found {len(keyword_papers)} papers from keyword search.")

        # 2. Seed DOIs Search
        if seed_dois:
            logger.info(f"Adding initial seed DOIs: {seed_dois}")
            seed_papers = self.get_papers_by_dois(seed_dois)
            all_candidates.extend(seed_papers)

        return all_candidates

    def get_snowball_candidates(
        self,
        df_scored: pd.DataFrame,
        top_n: int,
        related_limit: int = -1,
        threshold: float | None = None
    ) -> list[dict[str, Any]]:
        """
        スコア上位の論文から引用・被引用を取得する。
        top_n と threshold (スコア閾値) のうち、より多くの論文が含まれる方を採用する。
        """
        if df_scored.empty:
            return []

        # 1. Top N で絞り込み
        top_n_papers = df_scored.sort_values(by="relevance_score", ascending=False).head(top_n)

        # 2. Threshold で絞り込み (もし指定があれば)
        final_papers = top_n_papers
        if threshold is not None:
            threshold_papers = df_scored[df_scored["relevance_score"] >= threshold]
            if len(threshold_papers) > len(top_n_papers):
                logging.info(f"Using threshold {threshold} yielded {len(threshold_papers)} papers, which is more than top_n {top_n}.")
                final_papers = threshold_papers

        # ソートはしておく
        top_papers = final_papers.sort_values(by="relevance_score", ascending=False)
        candidates = []

        for _, row in top_papers.iterrows():
            doi = row.get("doi")
            if doi:
                related = self.get_related_papers(doi, limit=related_limit)
                candidates.extend(related)

        return candidates

    def process_papers(
        self,
        papers: list[dict[str, Any]],
        exclude_dois: set[str],
        min_citations: int,
        year_range: list[int]
    ) -> pd.DataFrame:
        """収集したRawデータをDataFrame化し、フィルタリング・補完を行う"""
        if not papers:
            return pd.DataFrame()

        df = pd.DataFrame(papers)

        # DOIの抽出と重複排除
        def get_doi(x):
            return x.get("DOI") if isinstance(x, dict) else None

        if "doi" not in df.columns:
            if "externalIds" in df.columns:
                df["doi"] = df["externalIds"].apply(get_doi)
            else:
                # externalIdsもdoiもない場合は処理不能として除外
                df["doi"] = None

        # DOIのない論文はスキップ
        df = df.dropna(subset=["doi"])
        logger.info(f"Dropped {len(papers) - len(df)} papers without DOI.")

        # 既知のDOIを除外
        df = df[~df["doi"].isin(exclude_dois)]

        # 今回のバッチ内での重複排除
        logger.info(f"Dropped {sum(df.duplicated(subset=["doi"]))} duplicate papers.")
        df = df.drop_duplicates(subset=["doi"])

        if df.empty:
            logger.info("No new unique papers found after DOI filtering.")
            return df

        # 基本フィルタリング (引用数、年)
        if "citationCount" in df.columns:
            inds = df["citationCount"] >= min_citations
            df = df[inds]
            logger.info(f"Dropped {sum(~inds)} papers with less than {min_citations} citations.")
        if "year" in df.columns and len(year_range) == 2:
            inds = (df["year"] >= year_range[0]) & (df["year"] <= year_range[1])
            df = df[inds]
            logger.info(f"Dropped {sum(~inds)} papers outside of year range {year_range}.")

        if df.empty:
            logger.info("No papers passed criteria (citations/year).")
            return df

        # 抄録の補完
        df = self._fill_missing_abstracts_with_arxiv(df)

        # 抄録がない論文を最終的にフィルタリング
        before_drop = len(df)
        df = df[df["abstract"].str.strip().astype(bool) & df["abstract"].notna()]
        dropped_count = before_drop - len(df)
        if dropped_count > 0:
            logger.info(f"Dropped {dropped_count} papers that still have no abstract after ArXiv fill attempt.")

        logger.info(f"Papers ready for screening: {len(df)}")
        return df

    def _fill_missing_abstracts_with_arxiv(self, df: pd.DataFrame) -> pd.DataFrame:
        """抄録が欠けている論文を ArXiv で検索して補完する"""
        missing_mask = df["abstract"].isna() | (df["abstract"] == "")
        missing_count = missing_mask.sum()
        if missing_count == 0:
            return df

        logger.info(f"Attempting to fill missing abstracts for {missing_count} papers using ArXiv API...")
        client = arxiv.Client()

        # イテレーション部分をtqdmでラップしてプログレスバー化
        for idx, row in tqdm(df[missing_mask].iterrows(), total=missing_count, desc="Filling abstracts from ArXiv"):
            title = row["title"]
            doi = row.get("doi")
            query = f'ti:"{title}"'
            if doi:
                query += f' OR id:{doi}'

            search = arxiv.Search(query=query, max_results=1)
            try:
                results = list(client.results(search))
                if results:
                    best_match = results[0]
                    if title.lower() in best_match.title.lower() or best_match.title.lower() in title.lower():
                        df.at[idx, "abstract"] = best_match.summary
                        # logger.info(f"Filled abstract for: {title}")  # ループ内ログは抑制
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Failed to fetch abstract from ArXiv for {title}: {e}")

        return df
