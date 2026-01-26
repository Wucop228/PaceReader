from datetime import datetime

from pydantic import BaseModel, model_validator, Field

from app.text.enums import SourceType, SummaryStatus, SummaryLevel


class SummaryCreateResponse(BaseModel):
    summary_id: str
    document_id: str
    status: SummaryStatus
    level: SummaryLevel
    summary_text: str | None = None
    error: str | None = None

    model_config = {"from_attributes": True}


class SummaryResponse(BaseModel):
    id: str
    document_id: str
    status: SummaryStatus
    level: SummaryLevel
    summary_text: str | None
    model: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: str
    source_type: SourceType
    original_text: str
    file_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SummarizeRequest(BaseModel):
    file_path: str | None = None
    text: str | None = None
    level: SummaryLevel = SummaryLevel.MEDIUM
    model: str | None = None
    temperature: float = 0.2
    max_steps: int = 8

    @model_validator(mode='after')
    def validate_source(self):
        if self.file_path is None and self.text is None:
            raise ValueError("Нужно передать file_path ИЛИ text")

        if self.file_path is not None and self.text is not None:
            raise ValueError("Нельзя передать file_path И text одновременно")

        return self

class SpeedReadRequest(BaseModel):
    words_per_minute: int = Field(
        default=100,
        ge=50,
        le=1000,
    )


class SpeedReadInfo(BaseModel):
    summary_id: str
    word_count: int
    estimated_duration_seconds: int
    words_per_minute: int

    model_config = {"from_attributes": True}