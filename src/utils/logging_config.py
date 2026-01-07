import logging
from pathlib import Path

from src.utils.constants import APP_LOGGER_NAME


def setup_logging(log_dir: Path, level: str = "INFO") -> None:
    """ロギングの設定を行う (ルートロガーではなく 'review' ロガーを親にする)"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8-sig")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # アプリケーション固有の親ロガーを取得
    app_logger = logging.getLogger(APP_LOGGER_NAME)
    app_logger.setLevel(numeric_level)

    # ルートロガーへの伝播を停止
    app_logger.propagate = False

    # 二重出力を防ぐために既存のハンドラーをクリア
    if app_logger.hasHandlers():
        app_logger.handlers.clear()

    app_logger.addHandler(file_handler)
    app_logger.addHandler(stream_handler)
