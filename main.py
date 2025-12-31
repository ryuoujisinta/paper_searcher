import logging
import os
from pathlib import Path
import pandas as pd

from src.core.collector import S2Collector
from src.core.screener import PaperScreener
from src.utils.constants import APP_LOGGER_NAME
from src.utils.io_utils import (
    create_run_directory,
    load_config
)
from src.utils.logging_config import setup_logging

logger = logging.getLogger(f"{APP_LOGGER_NAME}.main")


def main():
    # 1. 初期設定
    config = load_config()
    run_dir = create_run_directory(config.project_name)
    setup_logging(run_dir, level=config.logging.level)

    logger.info(f"Starting pipeline for project: {config.project_name}")
    logger.info(f"Data will be saved in: {run_dir}")

    # ~/.env から Gemini API Key を読み込む
    from dotenv import load_dotenv
    env_path = Path.home() / ".env"
    load_dotenv(dotenv_path=env_path)
    google_key = os.getenv("GOOGLE_API_KEY") or ""

    if not google_key:
        logger.error("GOOGLE_API_KEY is missing. Please set it in ~/.env")
        return

    # --- Iterative Pipeline ---
    all_papers_df = pd.DataFrame()
    processed_dois = set()

    # 1. Initial Keyword Search
    keywords = config.search_criteria.keywords
    nl_query = config.search_criteria.natural_language_query or " ".join(keywords)
    logger.info(f"Initial keyword search for: {keywords}")

    collector = S2Collector()
    screener = PaperScreener(api_key=google_key, model_name=config.llm_settings.model_screening)

    # 初回のシードDOIがあれば取得
    if config.search_criteria.seed_paper_dois:
        logger.info(f"Adding initial seed DOIs: {config.search_criteria.seed_paper_dois}")
        seed_papers = collector.get_papers_by_dois(config.search_criteria.seed_paper_dois)
        new_papers = seed_papers
    else:
        new_papers = collector.search_by_keywords(keywords)

    for i in range(config.search_criteria.iterations):
        iteration_num = i + 1
        logger.info(f"--- Iteration {iteration_num}/{config.search_criteria.iterations} ---")

        if not new_papers:
            logger.warning("No new papers found in this iteration. Breaking loop.")
            break

        # 変換
        df_new = pd.DataFrame(new_papers)

        # DOIの抽出と重複排除
        def get_doi(x):
            return x.get("DOI") if isinstance(x, dict) else None

        if "doi" not in df_new.columns and "externalIds" in df_new.columns:
            df_new["doi"] = df_new["externalIds"].apply(get_doi)

        # 既知のDOIを除外
        df_new = df_new[~df_new["doi"].isin(processed_dois)]
        if df_new.empty:
            logger.info("No new unique papers found in this iteration.")
            break

        # 基本フィルタリング (引用数、年)
        min_citations = config.search_criteria.min_citations
        year_range = config.search_criteria.year_range

        if "citationCount" in df_new.columns:
            df_new = df_new[df_new["citationCount"] >= min_citations]
        if "year" in df_new.columns and len(year_range) == 2:
            df_new = df_new[(df_new["year"] >= year_range[0]) & (df_new["year"] <= year_range[1])]

        if df_new.empty:
            logger.info("No papers passed initial filtering in this iteration.")
            break

        # 抄録の補完
        df_new = collector._fill_missing_abstracts_with_arxiv(df_new)

        # 2. Scoring & Summarization (Phase 2 equivalent)
        logger.info(f"Scoring {len(df_new)} new papers...")
        df_scored = screener.screen_papers(df_new, nl_query)

        # 既読リストに追加
        new_dois = set(df_scored["doi"].dropna().unique())
        processed_dois.update(new_dois)

        # 全体リストに結合
        all_papers_df = pd.concat([all_papers_df, df_scored], ignore_index=True)

        # 3. Snowball Search (Next iteration seeds)
        if iteration_num < config.search_criteria.iterations:
            top_n = config.search_criteria.top_n_for_snowball
            # 現在のイテレーションで見つかった上位論文を取得
            top_papers = df_scored.sort_values(by="relevance_score", ascending=False).head(top_n)

            next_seeds = []
            for _, row in top_papers.iterrows():
                doi = row.get("doi")
                if doi:
                    related = collector.get_related_papers(doi)
                    next_seeds.extend(related)

            new_papers = next_seeds
            logger.info(f"Found {len(new_papers)} potential papers for next iteration via snowballing.")

    if all_papers_df.empty:
        logger.warning("No papers collected throughout iterations. Exiting.")
        return

    # 4. Sorting and Saving
    # 同一論文が複数イテレーションで現れる可能性（スコアが変わる可能性）を考慮し、最高スコアを残す
    final_df = all_papers_df.sort_values(by="relevance_score", ascending=False).drop_duplicates(subset=["doi"])

    # --- Phase 3: Extraction (Final Selection) ---
    threshold = config.search_criteria.screening_threshold
    df_for_extraction = final_df[final_df["relevance_score"] >= threshold].copy()
    logger.info(f"Total papers passed screening (score >= {threshold}): {len(df_for_extraction)}")

    if df_for_extraction.empty:
        logger.warning("No papers passed the screening threshold. Saving all scored papers instead.")
        final_data_csv = run_dir / "final" / "scored_papers_below_threshold.csv"
        final_df.to_csv(final_data_csv, index=False, encoding="utf-8-sig")
        return

    final_data_csv = run_dir / "final" / "final_review_matrix.csv"
    logger.info("--- Phase 3: Extraction (詳細抽出) ---")
    extractor = PaperExtractor(
        api_key=google_key,
        model_name=config.llm_settings.model_extraction
    )
    df_final = extractor.extract_info(df_for_extraction)

    # CSV形式で保存
    df_final.to_csv(final_data_csv, index=False, encoding="utf-8-sig")
    logger.info(f"Process complete! Final matrix saved to: {final_data_csv}")


if __name__ == "__main__":
    main()
