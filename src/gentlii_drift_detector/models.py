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
