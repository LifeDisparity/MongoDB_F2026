"""Model-proposed policy optimizer (LA-18).

Generates at most two evidence-linked candidates, enforces the immutable policy
controls, and selects with the frozen evaluator rule. The optional
model-backed proposer lives in :mod:`optimization.model_proposer` and is not
imported here so the core carries no provider dependency.
"""

from .optimizer import (
    MAX_CANDIDATES,
    Evaluator,
    Proposer,
    build_candidate,
    optimization_events,
    run_optimization,
)
from .types import ContextChange, OptimizationContext, ProposedPatch, ReviewChange

__all__ = [
    "MAX_CANDIDATES",
    "ContextChange",
    "Evaluator",
    "OptimizationContext",
    "ProposedPatch",
    "Proposer",
    "ReviewChange",
    "build_candidate",
    "optimization_events",
    "run_optimization",
]
