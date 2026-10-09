"""KMA Council — Source Registry (KMA-002).

Enkel, deterministisk och testbar registermodell för regulatoriska källor.
"""
from .models import (
    AuthorityLevel,
    Currentness,
    Source,
    SourceType,
    SourceVersion,
)
from .registry import SourceRegistry
from .validation import (
    DuplicateSourceError,
    SourceValidationError,
    SourceVersionValidationError,
    ValidationError,
)
from .utils import compute_checksum, deterministic_keys, normalize_for_hash

__all__ = [
    "AuthorityLevel",
    "Currentness",
    "Source",
    "SourceType",
    "SourceVersion",
    "SourceRegistry",
    "SourceValidationError",
    "SourceVersionValidationError",
    "DuplicateSourceError",
    "ValidationError",
    "compute_checksum",
    "deterministic_keys",
    "normalize_for_hash",
]
