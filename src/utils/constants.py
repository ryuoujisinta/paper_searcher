from pathlib import Path

APP_LOGGER_NAME = "review"
DEFAULT_CONFIG_PATH = Path("config.yml")
LAYOUT_CONFIG_PATH = Path("layout_config.yml")
DATA_DIR = Path("data")
PROMPTS_DIR = Path("prompts")
ASSETS_DIR = Path("assets")
CSS_FILE = ASSETS_DIR / "css" / "style.css"

CANDIDATE_COLUMNS = [
    "relevance_score",
    "title",
    "summary",
    "relevance_reason",
    "citationCount",
    "year",
    "doi",
    "url",
    "authors",
    "venue",
]
