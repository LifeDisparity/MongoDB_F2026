"""Serializable model records; credentials and prompt bodies are never records."""
from __future__ import annotations

from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ModelSettings(FrozenRecord):
    model_id: str | None = None
    run_token_budget: int = Field(default=150000, ge=1)
    run_max_model_calls: int = Field(default=24, ge=1, le=100)
    max_output_tokens: int = Field(default=2048, ge=16, le=32768)
    max_input_bytes: int = Field(default=120000, ge=1024, le=1000000)
    max_attempts: int = Field(default=2, ge=1, le=3)
    request_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    deadline_seconds: float = Field(default=120.0, gt=0, le=600)


class StructuredRequest(FrozenRecord):
    request_id: str = Field(min_length=1, max_length=200)
    instructions: str = Field(min_length=1, repr=False)
    input_text: str = Field(min_length=1, repr=False)
    purpose: Literal["investigation", "review", "optimization"] = "investigation"


class ModelBudget(FrozenRecord):
    """Checkpoint this entire record; unknown usage consumes its reservation."""
    token_limit: int = Field(ge=1)
    call_limit: int = Field(ge=1)
    known_tokens: int = Field(default=0, ge=0)
    reserved_unknown_tokens: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    unknown_usage_calls: int = Field(default=0, ge=0)
    preflight_calls: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def coherent(self):
        if self.unknown_usage_calls > self.model_calls:
            raise ValueError("Unknown usage calls cannot exceed model calls")
        if (self.unknown_usage_calls == 0) != (self.reserved_unknown_tokens == 0):
            raise ValueError("Unknown usage must retain a nonzero token reservation")
        return self

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.token_limit - self.known_tokens - self.reserved_unknown_tokens)

    @property
    def within_limits(self) -> bool:
        return (self.model_calls <= self.call_limit and
                self.known_tokens + self.reserved_unknown_tokens <= self.token_limit)


class TokenUsage(FrozenRecord):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def coherent(self):
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("Provider token totals are inconsistent")
        if self.cached_input_tokens is not None and self.cached_input_tokens > self.input_tokens:
            raise ValueError("Cached tokens exceed input tokens")
        if self.reasoning_tokens is not None and self.reasoning_tokens > self.output_tokens:
            raise ValueError("Reasoning tokens exceed output tokens")
        return self


class ModelFailure(FrozenRecord):
    code: str
    message: str
    retryable: bool = False


class AttemptRecord(FrozenRecord):
    attempt: int = Field(ge=1)
    stage: Literal["reserved", "settled"]
    started_at: str
    duration_seconds: float = Field(default=0.0, ge=0)
    outcome: str
    reserved_tokens: int = Field(ge=0)
    input_token_count: int = Field(ge=0)
    max_output_tokens: int = Field(ge=16)
    usage: TokenUsage | None = None
    response_id: str | None = None
    provider_request_id: str | None = None
    actual_model_id: str | None = None
    failure_code: str | None = None


Parsed = TypeVar("Parsed", bound=BaseModel)


class ModelResult(FrozenRecord, Generic[Parsed]):
    request_id: str
    model_id: str | None
    purpose: str
    status: Literal["completed", "failed", "unavailable", "budget_exhausted"]
    output: Parsed | None = None
    failure: ModelFailure | None = None
    attempts: tuple[AttemptRecord, ...] = ()
    budget: ModelBudget
    prompt_sha256: str
    schema_sha256: str
    duration_seconds: float = Field(ge=0)
    known_usage_tokens: int = Field(ge=0)
    usage_complete: bool
    budget_ok: bool
    total_cost: float | None = None
    cost_status: Literal["not_priced"] = "not_priced"
