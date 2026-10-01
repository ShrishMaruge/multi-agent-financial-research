from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    name: str
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


