import logging
from concurrent.futures import ThreadPoolExecutor

from google import genai
import pandas as pd
from pydantic import BaseModel, Field
from src.utils import get_prompt

logger = logging.getLogger(__name__)


class ScreeningResult(BaseModel):
    relevance_score: int = Field(description="Score from 0 to 10 indicating relevance to the research theme.")
    relevance_reason: str = Field(description="Brief reason for the assigned score.")


class PaperScreener:
    def __init__(self, api_key: str, model_name: str, max_workers: int = 5):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.max_workers = max_workers
        self.prompt_template = get_prompt("screening")

    def screen_papers(self, df: pd.DataFrame, research_scope: str) -> pd.DataFrame:
        """論文をLLMで並列にスクリーニングする"""
        logger.info(f"Starting parallel screening for {len(df)} papers with {self.max_workers} workers")

        def process_row(row):
            title = row.get("title", "No Title")
            abstract = row.get("abstract", "")

            if not abstract:
                logger.warning(f"Skipping screening for {title} due to missing abstract")
                return {"relevance_score": 0, "relevance_reason": "No abstract available"}

            try:
                score_data = self._call_llm(title, abstract, research_scope)
                return score_data.model_dump()
            except Exception:
                logger.exception(f"Error screening paper {title}")
                return {"relevance_score": 0, "relevance_reason": "LLM Error occurred"}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(lambda x: process_row(x[1]), df.iterrows()))

        # 元のDataFrameに結果を結合
        results_df = pd.DataFrame(results)
        df = pd.concat([df.reset_index(drop=True), results_df], axis=1)

        return df

    def _call_llm(self, title: str, abstract: str, research_scope: str) -> ScreeningResult:
        prompt = self.prompt_template.format(
            research_scope=research_scope,
            title=title,
            abstract=abstract
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ScreeningResult,
            }
        )

        return response.parsed
