import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from google import genai
import pandas as pd
from pydantic import BaseModel, Field
from src.constants import APP_LOGGER_NAME
from src.io_utils import ProgressTracker, get_prompt

logger = logging.getLogger(f"{APP_LOGGER_NAME}.extractor")


class ExtractionResult(BaseModel):
    problem: str = Field(description="The specific research problem addressed by the paper.")
    method: str = Field(description="The proposed method or algorithm name.")
    dataset: str = Field(description="The datasets used in the study.")
    metric: str = Field(description="Evaluation metrics and key results.")
    limitation: str = Field(description="Limitations or future work.")
    category: Literal["Method", "Survey", "Theory", "Application"] = Field(description="Category of the paper.")
    one_line_summary: str = Field(description="A one-line summary of the paper in Japanese.")


class PaperExtractor:
    def __init__(self, api_key: str, model_name: str, max_workers: int = 5):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.max_workers = max_workers
        self.prompt_template = get_prompt("extraction")

    def extract_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """高品質な関連論文から並列に詳細情報を抽出する"""
        logger.info(f"Starting parallel information extraction for {len(df)} papers with {self.max_workers} workers")

        progress = ProgressTracker(total=len(df), prefix="Extraction")

        def process_row(row):
            title = row.get("title", "No Title")
            abstract = row.get("abstract", "")

            try:
                extraction_data = self._call_llm(title, abstract)
                result = extraction_data.model_dump()
            except Exception:
                logger.exception(f"Error extracting info from paper {title}")
                result = {k: "Error" for k in ExtractionResult.model_fields.keys()}

            progress.update()
            return result

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(lambda x: process_row(x[1]), df.iterrows()))

        progress.close()

        # 元のDataFrameに結果を結合
        results_df = pd.DataFrame(results)
        df = pd.concat([df.reset_index(drop=True), results_df], axis=1)

        return df

    def _call_llm(self, title: str, abstract: str) -> ExtractionResult:
        prompt = self.prompt_template.format(
            title=title,
            abstract=abstract
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ExtractionResult,
            }
        )

        return response.parsed
