"""KMA Council — Council Orchestration errors (KMA-005).

Deterministiska feltyper for routing, intake, kontrakt och pipeline.
Inga regulatoriska sakpastaenden hor hemma har (AD-1).
"""
from __future__ import annotations

__all__ = [
    "CouncilError",
    "RoutingError",
    "IntakeError",
    "ContractLoadError",
    "PipelineError",
]


class CouncilError(ValueError):
    """Basfel for orkestreringen (KMA-005)."""


class RoutingError(CouncilError):
    """Okand fraga eller ogiltig route (eskalering, aldrig gissad route)."""


class IntakeError(CouncilError):
    """Saknad kritisk information vid intag (gate 3)."""


class ContractLoadError(CouncilError):
    """Kontrakt kan ej laddas eller valideras som data."""


class PipelineError(CouncilError):
    """Pipeline-fel: saknade bidrag, ogiltig ordning eller trasig gate."""
