from pydantic import BaseModel, Field


class SearchCriteria(BaseModel):
    keywords: list[str]
    natural_language_query: str = ""
    seed_paper_dois: list[str] = Field(default_factory=list)
    keyword_search_limit: int = 100
    max_related_papers: int = -1
    snowball_from_keywords_limit: int = 5
    min_citations: int = 10
    year_range: list[int] = Field(default_factory=lambda: [2000, 2025])
    screening_threshold: int = 7
    iterations: int = 1
    top_n_for_snowball: int = 5
    max_retries: int = 10


class LoggingConfig(BaseModel):
    level: str = "INFO"


class LLMSettings(BaseModel):
    model_screening: str = "gemini-2.0-flash-lite"
    max_screening_workers: int = 5


class Config(BaseModel):
    project_name: str
    search_criteria: SearchCriteria
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    llm_settings: LLMSettings


class ScreeningResult(BaseModel):
    relevance_score: int = Field(
        description="Score from 0 to 10 indicating relevance to the research theme."
    )
    relevance_reason: str = Field(
        description="Brief reason for the assigned score (in Japanese)."
    )
    summary: str = Field(description="A 1-2 sentence summary of the paper in Japanese.")
