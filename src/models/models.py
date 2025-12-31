from pydantic import BaseModel, Field


class SearchCriteria(BaseModel):
    keywords: list[str]
    natural_language_query: str = ""
    seed_paper_dois: list[str] = Field(default_factory=list)
    snowball_from_keywords_limit: int = 5
    min_citations: int = 10
    year_range: list[int] = Field(default_factory=lambda: [2000, 2025])
    screening_threshold: int = 7
    iterations: int = 1
    top_n_for_snowball: int = 5


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
