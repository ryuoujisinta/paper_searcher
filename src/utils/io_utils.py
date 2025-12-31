import shutil
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any
import pandas as pd

from src.utils.constants import DEFAULT_CONFIG_PATH, DATA_DIR, PROMPTS_DIR
from src.models.models import Config


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> Config:
    """設定ファイルを読み込んでPydanticでバリデーションする"""
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(**data)


def save_config(config: Config, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    """ConfigオブジェクトをYAMLファイルとして保存する"""
    data = config.model_dump()
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def get_prompt(prompt_name: str) -> str:
    """promptsディレクトリからプロンプトを読み込む"""
    prompt_path = PROMPTS_DIR / f"{prompt_name}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def create_run_directory(project_name: str) -> Path:
    """実行ごとのディレクトリを作成する"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = DATA_DIR / f"{timestamp}_{project_name}"

    # 必要なサブディレクトリの作成
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    (run_dir / "interim").mkdir(parents=True, exist_ok=True)
    (run_dir / "final").mkdir(parents=True, exist_ok=True)

    # 設定ファイルのコピー
    if DEFAULT_CONFIG_PATH.exists():
        shutil.copy(DEFAULT_CONFIG_PATH, run_dir / "config.yml")

    return run_dir


def save_checkpoint(data: Any, path: Path) -> None:
    """中間データを保存する (CSV または pickle)"""
    if isinstance(data, pd.DataFrame):
        if path.suffix == ".csv":
            data.to_csv(path, index=False, encoding="utf-8-sig")
        else:
            data.to_pickle(path)
    else:
        import pickle
        with open(path, "wb") as f:
            pickle.dump(data, f)


def load_checkpoint(path: Path) -> Any:
    """中間データを読み込む"""
    if path.suffix == ".csv":
        return pd.read_csv(path)
    if path.suffix == ".pkl":
        return pd.read_pickle(path)
    else:
        import pickle
        with open(path, "rb") as f:
            return pickle.load(f)


class ProgressTracker:
    """ThreadPoolExecutor 等の進捗を管理するためのシンプルなカウンタ"""
    def __init__(self, total: int, prefix: str = "Progress"):
        from tqdm import tqdm
        self.pbar = tqdm(total=total, desc=prefix)

    def update(self, n: int = 1):
        self.pbar.update(n)

    def close(self):
        self.pbar.close()
