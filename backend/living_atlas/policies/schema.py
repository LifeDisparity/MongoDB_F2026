"""Policy schema and immutable controls (LA-17).

A policy is an *executable* configuration for how future investigations
assemble context (LA-08) and route scope review. The self-improvement loop
(LA-18) may only propose changes to those two sections. Budgets, the configured
model, provenance and the evaluator are frozen fields: a proposal that changes
any of them is rejected before it can run, so a candidate can never widen its
own resource envelope or grade itself.

Every accepted version is content-addressed: ``configuration_sha256`` hashes the
whole configuration and ``policy_version`` is derived from it, so two identical
configurations share a version and any tampering is detectable. Parent version
and proposal metadata (who proposed it, which development failures motivated it)
are preserved on each derived version.

Wire shape reuses the integrator-owned ``contracts.Policy`` model; this module
never edits shared contracts.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from living_atlas.contracts.models import Policy

# Leaf paths a proposal is permitted to change. Everything else is immutable.
MUTABLE_PATHS: frozenset[tuple[str, ...]] = frozenset({
    ("context_policy", "mode"),
    ("review_policy", "mode"),
    ("review_policy", "retrieve_controls"),
})

# Top-level sections that are frozen; named for clearer rejection messages.
IMMUTABLE_SECTIONS: tuple[str, ...] = ("budget", "model", "evaluator", "provenance")

CONTEXT_MODES: frozenset[str] = frozenset({"ranked_passages", "experimental_context"})
REVIEW_MODES: frozenset[str] = frozenset({"on_conflict", "on_scope_ambiguity", "always"})

_MISSING = object()


class PolicyViolation(ValueError):
    """A proposal changed a frozen field or produced an invalid configuration."""

    def __init__(self, code: str, message: str, **details: object) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def default_configuration() -> dict:
    """The frozen baseline configuration (H0)."""
    return {
        "context_policy": {"mode": "ranked_passages"},
        "review_policy": {"mode": "on_conflict", "retrieve_controls": False},
        # Frozen sections below: not proposable by the optimizer.
        "budget": {"context_tokens": 1200, "max_passages": 8, "per_passage_overhead_tokens": 16},
        "model": {"model_id": "configured-model"},
        "evaluator": {"evaluator_id": "frozen-internal-v1"},
        "provenance": {"schema_version": 1, "transform_version": "policy_v1"},
    }


def configuration_sha256(configuration: dict) -> str:
    return sha256(json.dumps(
        configuration, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def _policy_version(digest: str) -> str:
    return "pol_" + digest[:16]


def validate_configuration(configuration: dict) -> None:
    """Structural and enum validation applied to every version, always."""
    if not isinstance(configuration, dict):
        raise PolicyViolation("invalid_configuration", "Configuration must be an object")

    context = configuration.get("context_policy")
    if not isinstance(context, dict) or context.get("mode") not in CONTEXT_MODES:
        raise PolicyViolation(
            "invalid_context_policy",
            "context_policy.mode must be one of " + ", ".join(sorted(CONTEXT_MODES)),
            allowed=sorted(CONTEXT_MODES),
        )

    review = configuration.get("review_policy")
    if not isinstance(review, dict) or review.get("mode") not in REVIEW_MODES:
        raise PolicyViolation(
            "invalid_review_policy",
            "review_policy.mode must be one of " + ", ".join(sorted(REVIEW_MODES)),
            allowed=sorted(REVIEW_MODES),
        )
    if not isinstance(review.get("retrieve_controls"), bool):
        raise PolicyViolation(
            "invalid_review_policy",
            "review_policy.retrieve_controls must be a boolean",
        )

    for section in IMMUTABLE_SECTIONS:
        if section not in configuration:
            raise PolicyViolation(
                "missing_frozen_section",
                f"Frozen section '{section}' is required and must be preserved verbatim",
                section=section,
            )


def default_policy(proposed_by: str = "bootstrap") -> dict:
    """Build the baseline H0 policy as a validated contract dict."""
    configuration = default_configuration()
    validate_configuration(configuration)
    digest = configuration_sha256(configuration)
    policy = Policy(
        policy_version=_policy_version(digest),
        parent_policy_version=None,
        configuration=configuration,
        configuration_sha256=digest,
        proposed_by=proposed_by,
        development_failure_ids=[],
        evaluation_id=None,
        selection_status="baseline",
    )
    return policy.model_dump(mode="json")


def _changed_paths(before: dict, after: dict, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    changed: set[tuple[str, ...]] = set()
    for key in set(before) | set(after):
        path = prefix + (key,)
        left = before.get(key, _MISSING)
        right = after.get(key, _MISSING)
        if isinstance(left, dict) and isinstance(right, dict):
            changed |= _changed_paths(left, right, path)
        elif left != right:
            changed.add(path)
    return changed


def _deep_merge(base: dict, patch: dict) -> dict:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def propose_policy(
    parent: dict, patch: dict, *,
    proposed_by: str,
    development_failure_ids: list[str] | None = None,
) -> dict:
    """Derive a proposed policy version from ``parent`` by applying ``patch``.

    Only leaves in :data:`MUTABLE_PATHS` may change. Any change to a frozen
    field (budget/model/evaluator/provenance) or to an unknown path raises
    :class:`PolicyViolation` before the version is created, so forbidden
    proposals never enter the optimizer flow. Allowed changes yield a new
    content-addressed version linked to its parent, ready for evaluation.
    """
    if not isinstance(patch, dict):
        raise PolicyViolation("invalid_patch", "Patch must be an object of configuration changes")
    parent_configuration = parent["configuration"]
    candidate = _deep_merge(parent_configuration, patch)
    changed = _changed_paths(parent_configuration, candidate)

    if not changed:
        raise PolicyViolation("no_change", "Proposal does not change any configuration field")

    forbidden = sorted(path for path in changed if path not in MUTABLE_PATHS)
    if forbidden:
        raise PolicyViolation(
            "immutable_field_change",
            "Proposal changes frozen fields: " + ", ".join(".".join(p) for p in forbidden),
            forbidden_paths=[".".join(p) for p in forbidden],
            mutable_paths=[".".join(p) for p in sorted(MUTABLE_PATHS)],
        )

    validate_configuration(candidate)
    digest = configuration_sha256(candidate)
    policy = Policy(
        policy_version=_policy_version(digest),
        parent_policy_version=parent["policy_version"],
        configuration=candidate,
        configuration_sha256=digest,
        proposed_by=proposed_by,
        development_failure_ids=list(development_failure_ids or []),
        evaluation_id=None,
        selection_status="proposed",
    )
    return policy.model_dump(mode="json")


def verify_integrity(policy: dict) -> None:
    """Confirm a policy's recorded hash and version match its configuration.

    Raises :class:`PolicyViolation` if the immutable version was altered after
    creation.
    """
    digest = configuration_sha256(policy["configuration"])
    if policy.get("configuration_sha256") != digest:
        raise PolicyViolation(
            "integrity_mismatch",
            "configuration_sha256 does not match the configuration",
            expected=digest, recorded=policy.get("configuration_sha256"),
        )
    if policy.get("policy_version") != _policy_version(digest):
        raise PolicyViolation(
            "integrity_mismatch",
            "policy_version is not derived from the configuration hash",
            expected=_policy_version(digest), recorded=policy.get("policy_version"),
        )


def resolve_context_settings(policy: dict) -> dict:
    """Extract the LA-08 context-assembly settings this policy selects.

    Mode is mutable; the token budget and passage cap come from the frozen
    budget section, so a policy change reorders attention without widening the
    resource envelope.
    """
    verify_integrity(policy)
    configuration = policy["configuration"]
    budget = configuration.get("budget", {})
    return {
        "mode": configuration["context_policy"]["mode"],
        "token_budget": budget.get("context_tokens", 1200),
        "max_passages": budget.get("max_passages"),
        "per_passage_overhead_tokens": budget.get("per_passage_overhead_tokens", 16),
    }
