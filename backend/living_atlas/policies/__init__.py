"""Policy schema and immutable controls (LA-17).

Content-addressed, immutable policy versions whose only proposable sections are
context assembly (LA-08) and scope review. Budgets, model, provenance and the
evaluator are frozen; proposals that touch them reject.
"""

from .schema import (
    CONTEXT_MODES,
    IMMUTABLE_SECTIONS,
    MUTABLE_PATHS,
    REVIEW_MODES,
    PolicyViolation,
    configuration_sha256,
    default_configuration,
    default_policy,
    propose_policy,
    resolve_context_settings,
    validate_configuration,
    verify_integrity,
)

__all__ = [
    "CONTEXT_MODES",
    "IMMUTABLE_SECTIONS",
    "MUTABLE_PATHS",
    "REVIEW_MODES",
    "PolicyViolation",
    "configuration_sha256",
    "default_configuration",
    "default_policy",
    "propose_policy",
    "resolve_context_settings",
    "validate_configuration",
    "verify_integrity",
]
