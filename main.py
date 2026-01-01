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

    # 1. Initial Collection
    keywords = config.search_criteria.keywords
    nl_query = config.search_criteria.natural_language_query or " ".join(keywords)
    logger.info(f"Initial search for keywords: {keywords}")

    collector = S2Collector()
    screener = PaperScreener(api_key=google_key, model_name=config.llm_settings.model_screening)

    # イテレーション管理
    next_candidates = []  # 次回の検索候補（raw dict list）

    # 初回候補の取得
    next_candidates = collector.collect_initial(
        keywords=keywords,
        seed_dois=config.search_criteria.seed_paper_dois
    )

    for i in range(config.search_criteria.iterations):
        iteration_num = i + 1
        logger.info(f"--- Iteration {iteration_num}/{config.search_criteria.iterations} ---")

        # 処理 & フィルタリング
        df_new = collector.process_papers(
            papers=next_candidates,
            exclude_dois=processed_dois,
            min_citations=config.search_criteria.min_citations,
            year_range=config.search_criteria.year_range
        )

        if df_new.empty:
            logger.info("No new papers to screen in this iteration.")
            break

        # --- Save Raw Data (Iterative) ---
        raw_csv_path = run_dir / "raw" / f"collected_papers_iter_{iteration_num}.csv"
        df_new.to_csv(raw_csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"Saved raw papers for iteration {iteration_num} to {raw_csv_path}")

        # 2. Scoring & Summarization
        logger.info(f"Scoring {len(df_new)} new papers...")
        df_scored = screener.screen_papers(df_new, nl_query)

        # 既読リスト更新
        new_dois = set(df_scored["doi"].dropna().unique())
        processed_dois.update(new_dois)

        # 全体リストに結合
        all_papers_df = pd.concat([all_papers_df, df_scored], ignore_index=True)

        # --- Save Interim Data (Cumulative) ---
        interim_csv_path = run_dir / "interim" / "screened_papers_cumulative.csv"
        all_papers_df.to_csv(interim_csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"Saved cumulative screened papers to {interim_csv_path}")

        # 3. Snowball Search (Next iteration seeds)
        if iteration_num < config.search_criteria.iterations:
            top_n = config.search_criteria.top_n_for_snowball
            logger.info(f"Collecting snowball candidates from top {top_n} papers...")
            next_candidates = collector.get_snowball_candidates(df_scored, top_n)
            logger.info(f"Found {len(next_candidates)} potential papers for next iteration.")
        else:
            next_candidates = []  # Loop ends

    if all_papers_df.empty:
        logger.warning("No papers collected throughout iterations. Exiting.")
        return

    # 4. Sorting and Saving
    # 同一論文が複数イテレーションで現れる可能性（スコアが変わる可能性）を考慮し、最高スコアを残す
    final_df = all_papers_df.sort_values(by="relevance_score", ascending=False).drop_duplicates(subset=["doi"])

    # --- Saving Final Results ---
    final_data_csv = run_dir / "final" / "final_review_matrix.csv"
    logger.info(f"Saving final sorted results to: {final_data_csv}")

    # 関連度スコアでソートして保存
    final_df.to_csv(final_data_csv, index=False, encoding="utf-8-sig")
    logger.info(f"Process complete! Saved {len(final_df)} papers.")


if __name__ == "__main__":
    main()
