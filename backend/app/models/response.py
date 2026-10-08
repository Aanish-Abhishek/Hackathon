from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    error_type: str = Field(description="Error or failure category found in the logs")
    suspected_root_cause: str = Field(description="Likely cause supported by code and log evidence")
    file: str = Field(description="Repository path of the implicated source file")
    function: str = Field(description="Function or method implicated by the evidence")
    suggested_fix: str = Field(description="Specific remediation for the suspected cause")
    severity: Literal["Critical", "High", "Medium", "Low", "Unknown"] = "Unknown"
    confidence: float = Field(default=0, ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    analyzed_files: list[str] = Field(default_factory=list)
    repository_files: list[str] = Field(default_factory=list)
    analysis_mode: str = "gpt"
