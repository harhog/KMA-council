"""KMA Council — Source Registry (KMA-002).

Valideringsfel, som lyfts vid modellinstansiering och registry-operationer.
"""
from __future__ import annotations

__all__ = [
    "SourceValidationError",
    "SourceVersionValidationError",
    "DuplicateSourceError",
    "ValidationError",
]


class SourceValidationError(ValueError):
    """Allmänt valideringsfel för en Source-post."""


class SourceVersionValidationError(ValueError):
    """Allmänt valideringsfel för en SourceVersion."""


class DuplicateSourceError(ValueError):
    """Källa med redan existerande source_id registrerades."""


class ValidationError(ValueError):
    """Allmänt valideringsfel i registry/API-lagret."""
