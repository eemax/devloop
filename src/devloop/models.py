from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class InputMode(str, Enum):
    STDIN = "stdin"
    FILE = "file"


class CwdMode(str, Enum):
    REPO = "repo"
    SNAPSHOT = "snapshot"


class FindingSeverity(str, Enum):
    BLOCKING = "blocking"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class CheckResultStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_RUN = "not_run"


class FinalStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    STALLED = "stalled"


class AgentConfig(BaseModel):
    name: str
    command: list[str]
    input_mode: InputMode = InputMode.STDIN
    cwd_mode: CwdMode = CwdMode.REPO

    @field_validator("command")
    @classmethod
    def command_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("agent command must not be empty")
        return value


class CheckSpec(BaseModel):
    name: str
    command: str
    timeout_secs: int = Field(default=300, ge=1)


class CheckConfig(BaseModel):
    required: list[CheckSpec] = Field(default_factory=list)
    advisory: list[CheckSpec] = Field(default_factory=list)


class ObservabilityConfig(BaseModel):
    max_inline_text_chars: int = Field(default=20_000, ge=0)


class RunConfig(BaseModel):
    repo: Path = Path(".")
    max_rounds: int = Field(default=2, ge=1)
    commit_on_success: bool = False
    create_branch: bool = True
    branch_prefix: str = "codex/devloop"
    require_clean_worktree: bool = True
    artifact_dir: Path = Path(".devloop/runs")
    timeout_secs: int = Field(default=1800, ge=1)


class Config(BaseModel):
    run: RunConfig
    agents: dict[str, AgentConfig]
    checks: CheckConfig = Field(default_factory=CheckConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    @model_validator(mode="after")
    def validate_required_agents(self) -> "Config":
        missing = [name for name in ("implementer", "auditor") if name not in self.agents]
        if missing:
            raise ValueError(f"missing required agent config entries: {', '.join(missing)}")
        return self

    @property
    def implementer(self) -> AgentConfig:
        return self.agents["implementer"]

    @property
    def auditor(self) -> AgentConfig:
        return self.agents["auditor"]


class PlanSpec(BaseModel):
    goal: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    body: str
    source_path: Path


class RunSpec(BaseModel):
    run_id: str
    trace_id: str = ""
    repo_root: Path
    base_commit: str
    artifact_dir: Path
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    goal: str
    acceptance_criteria: list[str]
    constraints: list[str]
    out_of_scope: list[str]
    checks: list[str]
    max_rounds: int
    commit_on_success: bool
    create_branch: bool
    branch_prefix: str
    implementer: AgentConfig
    auditor: AgentConfig
    plan_path: Path
    raw_plan: str


class AgentInvocationResult(BaseModel):
    name: str
    command: list[str]
    resolved_command: str | None = None
    cwd: Path
    input_mode: InputMode = InputMode.STDIN
    stdout: str
    stderr: str
    exit_code: int
    duration_secs: float
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    json_payload: dict[str, Any] | None = None


class ImplementerCriterionStatus(BaseModel):
    criterion: str
    status: str


class ImplementerCheckStatus(BaseModel):
    name: str
    status: str


class ImplementerReport(BaseModel):
    summary: str
    files_touched: list[str] = Field(default_factory=list)
    criteria_status: list[ImplementerCriterionStatus] = Field(default_factory=list)
    checks_attempted: list[ImplementerCheckStatus] = Field(default_factory=list)
    known_risks: list[str] = Field(default_factory=list)
    notes_for_auditor: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    id: str
    severity: FindingSeverity
    title: str
    file: str = ""
    evidence: str
    fix_hint: str = ""
    confidence: float = 0.5


class AuditReport(BaseModel):
    summary: str
    decision: str
    findings: list[Finding] = Field(default_factory=list)
    missing_tests: list[str] = Field(default_factory=list)


class CommandResult(BaseModel):
    name: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_secs: float
    required: bool

    @property
    def status(self) -> CheckResultStatus:
        if self.exit_code == 0:
            return CheckResultStatus.PASS
        if self.exit_code == 124:
            return CheckResultStatus.NOT_RUN
        return CheckResultStatus.FAIL


class RoundState(BaseModel):
    round_number: int
    changed_files: list[str] = Field(default_factory=list)
    implementer_result: AgentInvocationResult
    implementer_report: ImplementerReport
    audit_result: AgentInvocationResult
    audit_report: AuditReport
    checks: list[CommandResult] = Field(default_factory=list)
    blocking_findings: list[Finding] = Field(default_factory=list)
    diff_changed: bool = True


class RunOutcome(BaseModel):
    status: FinalStatus
    rounds_completed: int
    final_checks: list[CommandResult] = Field(default_factory=list)
    final_findings: list[Finding] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    commit_sha: str | None = None
    branch_name: str | None = None
    report_path: Path
    report_json_path: Path


class StopDecision(BaseModel):
    stop: bool
    status: FinalStatus | None = None
    reason: str = ""
