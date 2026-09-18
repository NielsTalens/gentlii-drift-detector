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
    user_needs: list[str]
    capabilities: list[str]
    strategic_goals: list[str]
    investment_themes: list[str]
    direction_signals: list[str]
    evidence_summary: str
    confidence: Literal["low", "medium", "high"]


class IssueObservationBatch(BaseModel):
    observations: list[IssueObservation]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class IssueExtractionResult(BaseModel):
    observations: list[IssueObservation] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)


class SupportedClaim(BaseModel):
    statement: str
    issue_numbers: list[int]
    confidence: Literal["low", "medium", "high"]


class Synthesis(BaseModel):
    observed_strategy: list[SupportedClaim]
    observed_strategic_goals: list[SupportedClaim]
    observed_product_vision: list[SupportedClaim]
    user_needs: list[SupportedClaim]
    capabilities: list[SupportedClaim]
    investment_themes: list[SupportedClaim]
    uncertainties: list[SupportedClaim]


class SynthesisResult(BaseModel):
    synthesis: Synthesis
    usage: Usage = Field(default_factory=Usage)
