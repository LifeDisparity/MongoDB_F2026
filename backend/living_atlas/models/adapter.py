"""Responses API adapter with bounded work and auditable provider usage.

The workflow owns durable state. Persist the checkpoint callback before an
inference starts and after it settles. An interrupted call's reservation stays
unknown until usage is reconciled; never relabel that uncertainty as zero cost.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import re
import time
from typing import TypeVar

from openai import AsyncOpenAI, APIConnectionError, APIError, APIStatusError, APITimeoutError
from pydantic import BaseModel, ValidationError

from .types import (
    AttemptRecord, ModelBudget, ModelFailure, ModelResult, ModelSettings,
    StructuredRequest, TokenUsage,
)

Parsed = TypeVar("Parsed", bound=BaseModel)
Checkpoint = Callable[[AttemptRecord, ModelBudget], Awaitable[None]]


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _strict_schema(response_model):
    """Normalize Pydantic objects into the documented strict JSON-schema subset."""
    schema = deepcopy(response_model.model_json_schema())
    def normalize(node):
        if isinstance(node, list):
            for value in node:
                normalize(value)
        elif isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                if node.get("additionalProperties") not in (None, False):
                    raise ValueError("Structured output objects must have explicit named fields")
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for field in ("properties", "$defs", "definitions"):
                for value in node.get(field, {}).values():
                    normalize(value)
            for field in ("items", "anyOf", "allOf", "oneOf", "not"):
                if field in node:
                    normalize(node[field])
    normalize(schema)
    if schema.get("type") != "object":
        raise ValueError("Structured response must be a Pydantic object model")
    return schema


def _usage(response):
    value = getattr(response, "usage", None)
    if value is None:
        return None
    try:
        return TokenUsage(
            input_tokens=value.input_tokens, output_tokens=value.output_tokens,
            total_tokens=value.total_tokens,
            cached_input_tokens=getattr(getattr(value, "input_tokens_details", None), "cached_tokens", None),
            reasoning_tokens=getattr(getattr(value, "output_tokens_details", None), "reasoning_tokens", None),
        )
    except (ValidationError, AttributeError):
        return None


def _failure(exc):
    # Provider error bodies may contain prompts or credentials: do not serialize them.
    if isinstance(exc, (TimeoutError, APITimeoutError)):
        return ModelFailure(code="provider_timeout", message="The provider request timed out; usage may be unknown.", retryable=True)
    if isinstance(exc, APIConnectionError):
        return ModelFailure(code="provider_connection", message="The provider connection failed; usage may be unknown.", retryable=True)
    if isinstance(exc, APIStatusError):
        status = exc.status_code
        retryable = status in {408, 409, 429} or status >= 500
        code = "provider_authentication" if status in {401, 403} else "provider_rate_limit" if status == 429 else "provider_rejected"
        return ModelFailure(code=code, message=f"The provider returned HTTP {status}.", retryable=retryable)
    return ModelFailure(code="provider_error", message="The provider request failed.")


class StructuredModelAdapter:
    """Create with server settings only; requests cannot override model or limits."""
    def __init__(self, settings: ModelSettings, *, api_key: str | None):
        self._settings = settings
        # No arbitrary base URL: credentials go only to the configured OpenAI API.
        self._client = AsyncOpenAI(
            api_key=api_key, max_retries=0,
            timeout=settings.request_timeout_seconds,
            base_url="https://api.openai.com/v1",
        ) if api_key and settings.model_id else None

    @classmethod
    def from_env(cls, environment: Mapping[str, str] | None = None):
        env = os.environ if environment is None else environment
        settings = ModelSettings(
            model_id=env.get("MODEL_ID", "").strip() or None,
            run_token_budget=int(env.get("RUN_TOKEN_BUDGET", "150000")),
            run_max_model_calls=int(env.get("RUN_MAX_MODEL_CALLS", "24")),
            max_output_tokens=int(env.get("MODEL_MAX_OUTPUT_TOKENS", "2048")),
            max_input_bytes=int(env.get("MODEL_MAX_INPUT_BYTES", "120000")),
            max_attempts=int(env.get("MODEL_MAX_ATTEMPTS", "2")),
            request_timeout_seconds=float(env.get("MODEL_TIMEOUT_SECONDS", "60")),
            deadline_seconds=float(env.get("MODEL_DEADLINE_SECONDS", "120")),
        )
        return cls(settings, api_key=env.get("OPENAI_API_KEY", "").strip() or None)

    @property
    def settings(self):
        return self._settings

    @property
    def available(self):
        return self._client is not None

    def status(self):
        """Safe health information; this never contacts the provider."""
        return {"configured": self.available, "model_id": self.settings.model_id,
                "error_code": None if self.available else "model_not_configured"}

    def new_budget(self):
        return ModelBudget(token_limit=self.settings.run_token_budget,
                           call_limit=self.settings.run_max_model_calls)

    async def close(self):
        if self._client is not None:
            await self._client.close()

    async def generate(self, request: StructuredRequest, response_model: type[Parsed],
                       budget: ModelBudget, *, checkpoint: Checkpoint | None = None) -> ModelResult[Parsed]:
        started = time.monotonic()
        deadline = started + self.settings.deadline_seconds
        schema = _strict_schema(response_model)
        prompt_hash = _digest([request.instructions, request.input_text])
        schema_hash = _digest(schema)
        attempts = []
        current = budget

        def result(status, failure=None, output=None):
            return ModelResult[response_model](
                request_id=request.request_id, model_id=self.settings.model_id,
                purpose=request.purpose, status=status, output=output, failure=failure,
                attempts=tuple(attempts), budget=current,
                prompt_sha256=prompt_hash, schema_sha256=schema_hash,
                duration_seconds=time.monotonic() - started,
                known_usage_tokens=sum(row.usage.total_tokens for row in attempts if row.usage is not None),
                usage_complete=current.unknown_usage_calls == 0,
                budget_ok=current.within_limits,
            )

        if (budget.token_limit != self.settings.run_token_budget or
                budget.call_limit != self.settings.run_max_model_calls):
            return result("failed", ModelFailure(code="budget_mismatch", message="Budget limits differ from immutable server settings."))
        if not self.available:
            return result("unavailable", ModelFailure(code="model_not_configured", message="Set server-side OPENAI_API_KEY and MODEL_ID to enable real model calls."))
        format_name = re.sub(r"[^A-Za-z0-9_-]", "_", response_model.__name__)[:64] or "model_output"
        params = {
            "model": self.settings.model_id, "instructions": request.instructions,
            "input": request.input_text, "truncation": "disabled",
            "text": {"format": {"type": "json_schema", "name": format_name,
                                "strict": True, "schema": schema}},
        }
        if len(json.dumps(params, ensure_ascii=False).encode()) > self.settings.max_input_bytes:
            return result("budget_exhausted", ModelFailure(code="context_too_large", message="The bounded context packet exceeds the server input limit."))
        if not current.within_limits or current.model_calls >= current.call_limit:
            return result("budget_exhausted", ModelFailure(code="budget_exhausted", message="The model budget is exhausted."))

        # Count the exact same instructions, input and output schema sent below.
        # This is a preflight call, not a fabricated model token-usage measurement.
        current = current.model_copy(update={"preflight_calls": current.preflight_calls + 1})
        try:
            async with asyncio.timeout_at(deadline):
                counted = await self._client.responses.input_tokens.count(
                    **params, timeout=min(self.settings.request_timeout_seconds, deadline - time.monotonic()),
                )
            input_tokens = counted.input_tokens
            if type(input_tokens) is not int or input_tokens < 0:
                raise ValueError("Invalid provider token count")
        except (APIError, TimeoutError) as exc:
            return result("failed", _failure(exc))
        except ValueError:
            return result("failed", ModelFailure(code="invalid_token_count", message="The provider did not return a valid input count."))

        for number in range(1, self.settings.max_attempts + 1):
            max_output = min(self.settings.max_output_tokens, current.remaining_tokens - input_tokens)
            if current.model_calls >= current.call_limit or max_output < 16:
                return result("budget_exhausted", ModelFailure(code="budget_exhausted", message="Remaining budget cannot cover the input and a bounded response."))
            if time.monotonic() >= deadline:
                return result("failed", ModelFailure(code="deadline_exceeded", message="The model request deadline expired."))
            reserved = input_tokens + max_output
            attempt_started = time.monotonic()
            record = AttemptRecord(
                attempt=number, stage="reserved", started_at=datetime.now(timezone.utc).isoformat(),
                outcome="in_flight", reserved_tokens=reserved, input_token_count=input_tokens,
                max_output_tokens=max_output,
            )
            current = current.model_copy(update={
                "model_calls": current.model_calls + 1,
                "unknown_usage_calls": current.unknown_usage_calls + 1,
                "reserved_unknown_tokens": current.reserved_unknown_tokens + reserved,
            })
            if checkpoint is not None:
                # A failed reservation write prevents inference from starting.
                await checkpoint(record, current)
            response = None
            failure = None
            output = None
            failed_request_id = None
            try:
                async with asyncio.timeout_at(deadline):
                    response = await self._client.responses.create(
                        **params, max_output_tokens=max_output, store=False,
                        timeout=min(self.settings.request_timeout_seconds, max(0.001, deadline - time.monotonic())),
                    )
            except (APIError, TimeoutError) as exc:
                failure = _failure(exc)
                failed_request_id = getattr(exc, "request_id", None)
            usage = _usage(response) if response is not None else None
            if usage is not None:
                current = current.model_copy(update={
                    "known_tokens": current.known_tokens + usage.total_tokens,
                    "unknown_usage_calls": current.unknown_usage_calls - 1,
                    "reserved_unknown_tokens": current.reserved_unknown_tokens - reserved,
                })
            if response is not None:
                if any(getattr(part, "type", None) == "refusal"
                       for item in response.output if getattr(item, "type", None) == "message"
                       for part in item.content):
                    failure = ModelFailure(code="model_refusal", message="The model declined this structured request.")
                elif response.status != "completed":
                    failure = ModelFailure(code="incomplete_response", message="The provider response did not complete.")
                elif usage is None:
                    failure = ModelFailure(code="usage_unavailable", message="Provider usage is missing or inconsistent; the reservation remains unknown.")
                elif not current.within_limits or usage.total_tokens > reserved:
                    failure = ModelFailure(code="budget_invariant_failed", message="Reported usage exceeded the reserved token budget.")
                else:
                    try:
                        output = response_model.model_validate_json(response.output_text, strict=True, extra="forbid")
                    except (ValidationError, ValueError):
                        failure = ModelFailure(code="invalid_structured_output", message="The model output failed the required structured schema.")
            record = record.model_copy(update={
                "stage": "settled", "duration_seconds": time.monotonic() - attempt_started,
                "outcome": "completed" if output is not None else "failed", "usage": usage,
                "response_id": getattr(response, "id", None),
                "provider_request_id": getattr(response, "_request_id", None) or failed_request_id,
                "actual_model_id": getattr(response, "model", None),
                "failure_code": failure.code if failure is not None else None,
            })
            attempts.append(record)
            if checkpoint is not None:
                await checkpoint(record, current)
            if output is not None:
                return result("completed", output=output)
            if failure is None:
                failure = ModelFailure(code="empty_response", message="The provider returned no usable response.")
            if not failure.retryable or number == self.settings.max_attempts:
                return result("failed", failure)
            delay = min(float(2 ** (number - 1)), max(0.0, deadline - time.monotonic()))
            if delay:
                await asyncio.sleep(delay)
        return result("failed", ModelFailure(code="attempts_exhausted", message="The bounded attempts were exhausted."))
