import logging
import os
from pathlib import Path

from src.collector import S2Collector
from src.extractor import PaperExtractor
from src.screener import PaperScreener
from src.constants import APP_LOGGER_NAME
from src.io_utils import (create_run_directory, load_checkpoint, load_config,
                          save_checkpoint)
from src.logging_config import setup_logging

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

    # --- Phase 1: Collection ---
    raw_data_path = run_dir / "raw" / "collected_papers.csv"
    if raw_data_path.exists():
        logger.info("Found Phase 1 checkpoint. Loading...")
        df_collected = load_checkpoint(raw_data_path)
    else:
        logger.info("--- Phase 1: Collection (広範な収集) ---")
        collector = S2Collector()
        criteria = config.search_criteria
        df_collected = collector.collect(
            keywords=criteria.keywords,
            seed_dois=criteria.seed_paper_dois,
            min_citations=criteria.min_citations,
            year_range=criteria.year_range,
            snowball_from_keywords_limit=criteria.snowball_from_keywords_limit
        )
        save_checkpoint(df_collected, raw_data_path)
        logger.info(f"Phase 1 complete. Collected {len(df_collected)} papers.")

    if df_collected.empty:
        logger.warning("No papers collected. Exiting.")
        return

    # --- Phase 2: Screening ---
    interim_data_path = run_dir / "interim" / "screened_papers.csv"
    if interim_data_path.exists():
        logger.info("Found Phase 2 checkpoint. Loading...")
        df_screened = load_checkpoint(interim_data_path)
    else:
        logger.info("--- Phase 2: Screening (選別) ---")
        screener = PaperScreener(
            api_key=google_key,
            model_name=config.llm_settings.model_screening
        )
        research_scope = f"Focus on: {', '.join(config.search_criteria.keywords)}"
        df_screened = screener.screen_papers(df_collected, research_scope)
        save_checkpoint(df_screened, interim_data_path)
        logger.info("Phase 2 complete.")

    # 関連度スコアでフィルタリング
    threshold = config.search_criteria.screening_threshold
    df_for_extraction = df_screened[df_screened["relevance_score"] >= threshold].copy()
    logger.info(f"Papers passed screening (score >= {threshold}): {len(df_for_extraction)}")

    if df_for_extraction.empty:
        logger.warning("No papers passed screening. Exiting.")
        return

    # --- Phase 3: Extraction ---
    final_data_csv = run_dir / "final" / "final_review_matrix.csv"
    logger.info("--- Phase 3: Extraction (情報抽出) ---")
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
