from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None


class SessionResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: int
    session_id: int
    original_filename: str
    company_name: str | None
    fiscal_year: str | None
    status: str
    page_count: int
    chunk_count: int
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetricResponse(BaseModel):
    id: int
    metric_name: str
    metric_value: str
    period: str | None
    source_page: int
    evidence: str
    confidence: float

    model_config = ConfigDict(from_attributes=True)


class RedFlagResponse(BaseModel):
    id: int
    category: str
    severity: str
    title: str
    explanation: str
    source_page: int
    evidence: str
    confidence: float
    confidence_explanation: str
    matched_signals: str

    model_config = ConfigDict(from_attributes=True)


class ChatHistoryItem(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=6000)


class ResearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1500)
    document_ids: list[int] = Field(min_length=1)
    history: list[ChatHistoryItem] = Field(default_factory=list)