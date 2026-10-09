"""KMA Council — Source Registry (KMA-002).

Idempotent, deterministisk och testbar registryoperation för
regulatoriska källor. Inga modellanrop, inget RAG, inga externa beroenden
förutom den valda modellen.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .models import Currentness, Source, SourceVersion
from .validation import (
    DuplicateSourceError,
    SourceValidationError,
    SourceVersionValidationError,
)

__all__ = [
    "SourceRegistry",
    "SourceRegistryError",
]


class SourceRegistryError(ValueError):
    """Allmänt registryfel."""


class SourceRegistry:
    """Idempotent registry av källor.

    - Registera: source_id måste vara unikt. Dubbler → DuplicateSourceError.
    - Lookup: get(source_id) → Source | None (ingen raise vid saknad).
    - Currentness: expose current() / historical() / unknown().
    - Deterministisk serialisering: to_dict() → kanonisk ordning.
    - Checksumma: register(source, checksum=...) lagras i posten.
    """

    def __init__(self, sources: list[Source] | None = None) -> None:
        self._sources: dict[str, Source] = {}
        for source in sources or []:
            self.register(source)

    # ------------------------------------------------------------------
    # Core: register
    # ------------------------------------------------------------------
    def register(self, source: Source, *, checksum: str | None = None) -> Source:
        """Registrera source. Idempotentt: samma source_id ersätts inte
        (undantag görs med clear()). Versionstatus och checksumma lagras."""
        if not source.source_id:
            raise SourceValidationError("source_id är obligatoriskt")
        if source.source_id in self._sources:
            raise DuplicateSourceError(
                f"Källa med source_id '{source.source_id}' finns redan"
            )
        if checksum is not None:
            source.checksum = checksum
        self._sources[source.source_id] = source
        return source

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def get(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def has(self, source_id: str) -> bool:
        return source_id in self._sources

    # ------------------------------------------------------------------
    # List & currentness
    # ------------------------------------------------------------------
    def all(self, *, include_historical: bool = False) -> list[Source]:
        if include_historical:
            return list(self._sources.values())
        return [
            s for s in self._sources.values() if s.version_status is Currentness.CURRENT
        ]

    def current(self) -> list[Source]:
        return [s for s in self._sources.values() if s.is_current]

    def historical(self) -> list[Source]:
        return [s for s in self._sources.values() if s.is_historical]

    def unknown(self) -> list[Source]:
        return [s for s in self._sources.values() if s.is_unknown]

    # ------------------------------------------------------------------
    # Checksum
    # ------------------------------------------------------------------
    def checksum_of(self, source_id: str) -> str | None:
        source = self._sources.get(source_id)
        return source.checksum if source is not None else None

    # ------------------------------------------------------------------
    # Serialisering
    # ------------------------------------------------------------------
    def to_dict(self, *, include_none: bool = False) -> dict[str, Any]:
        return {
            sid: s.to_dict(include_none=include_none)
            for sid, s in sorted(self._sources.items())
        }

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def clear(self) -> None:
        self._sources.clear()

    def count(self) -> int:
        return len(self._sources)

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, source_id: object) -> bool:
        return isinstance(source_id, str) and source_id in self._sources

    def __iter__(self):
        return iter(self._sources.values())

    def __repr__(self) -> str:
        return f"<SourceRegistry count={self.count()}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SourceRegistry):
            return NotImplemented
        return self._sources == other._sources
