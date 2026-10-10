"""KMA Council - Workflows, feltyper (KMA-006).

Deterministiska fel for workflow-val, intake och route.
Inga regulatoriska sakpastaenden har (AD-1).
"""
from __future__ import annotations

__all__ = [
    "WorkflowError",
    "UnknownWorkflowError",
    "WorkflowIntakeError",
    "WorkflowRouteError",
]


class WorkflowError(ValueError):
    """Basfel for workflow-lagret (KMA-006)."""


class UnknownWorkflowError(WorkflowError):
    """Okant workflow-id (eskalera, gissa aldrig)."""


class WorkflowIntakeError(WorkflowError):
    """Ogiltig intake-typ eller okanda nycklar (valideringsfel, ej beslut)."""


class WorkflowRouteError(WorkflowError):
    """Ogiltig route-hint for workflow (t.ex. G utan RESEARCH)."""
