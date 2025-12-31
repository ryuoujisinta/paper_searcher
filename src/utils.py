import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
import yaml


class SearchCriteria(BaseModel):
    keywords: list[str]
    seed_paper_dois: list[str] = Field(default_factory=list)
    snowball_from_keywords_limit: int = 5
    min_citations: int = 10
    year_range: list[int] = Field(default_factory=lambda: [2000, 2025])
    screening_threshold: int = 7


class LoggingConfig(BaseModel):
    level: str = "INFO"


class LLMSettings(BaseModel):
    model_screening: str = "gemini-2.0-flash-lite"
    model_extraction: str = "gemini-2.0-flash-lite"


class Config(BaseModel):
    project_name: str
    search_criteria: SearchCriteria
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    llm_settings: LLMSettings


def setup_logging(log_dir: Path, level: str = "INFO") -> None:
    """ロギングの設定を行う"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


def load_config(config_path: str = "config.yml") -> Config:
    """設定ファイルを読み込んでPydanticでバリデーションする"""
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(**data)


def get_prompt(prompt_name: str) -> str:
    """promptsディレクトリからプロンプトを読み込む"""
    prompt_path = Path("prompts") / f"{prompt_name}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def create_run_directory(project_name: str) -> Path:
    """実行ごとのディレクトリを作成する"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(f"data/{timestamp}_{project_name}")

    # 必要なサブディレクトリの作成
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    (run_dir / "interim").mkdir(parents=True, exist_ok=True)
    (run_dir / "final").mkdir(parents=True, exist_ok=True)

    # 設定ファイルのコピー
    if os.path.exists("config.yml"):
        shutil.copy("config.yml", run_dir / "config.yml")

    return run_dir


def save_checkpoint(data: Any, path: Path) -> None:
    """中間データを保存する (pickle または pandas)"""
    import pandas as pd
    if isinstance(data, pd.DataFrame):
        data.to_pickle(path)
    else:
        import pickle
        with open(path, "wb") as f:
            pickle.dump(data, f)


def load_checkpoint(path: Path) -> Any:
    """中間データを読み込む"""
    import pandas as pd
    if path.suffix == ".pkl":
        return pd.read_pickle(path)
    else:
        import pickle
        with open(path, "rb") as f:
            return pickle.load(f)
