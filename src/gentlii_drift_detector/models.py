from typing import Literal

from pydantic import BaseModel, Field


class Issue(BaseModel):
    number: int
    title: str
    body: str
    closed_at: str | None = None
    labels: list[str] = Field(default_factory=list)


class ParseResult(BaseModel):
    issues: list[Issue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IssueObservation(BaseModel):
    issue_number: int
    title: str
    delivery_status: Literal["delivered", "not_delivered", "uncertain"]
    user_needs: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    strategic_goals: list[str] = Field(default_factory=list)
    investment_themes: list[str] = Field(default_factory=list)
    direction_signals: list[str] = Field(default_factory=list)
    evidence_summary: str
    confidence: Literal["low", "medium", "high"]


class IssueObservationBatch(BaseModel):
    observations: list[IssueObservation] = Field(default_factory=list)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class IssueExtractionResult(BaseModel):
    observations: list[IssueObservation] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
