"""KMA Council — Evidence Engine (KMA-003).

Deterministisk evidensmodell för regulatoriska påståenden om KMA-regler.
Domänmodell: docs/KMA_ARCHITECTURE.md §4 (Evidence) och §6 (Evidence gate).
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kma.sources import AuthorityLevel, Currentness, Source, SourceType, SourceVersion
from kma.sources.utils import compute_checksum

__all__ = ["Evidence", "EvidenceStatus"]


class EvidenceStatus(str, Enum):
    """Gate-status för evidens (sätts av Evidence Engine, aldrig av agent)."""

    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    HISTORICAL = "HISTORICAL"
    CONFLICTING = "CONFLICTING"


class Evidence(BaseModel):
    """Registreringspost för en evidens som stöder ett påstående.

    source_version är alltid exakt "source_id/version" och pekar på en
    bestämd SourceVersion (KMA-003 regel 8). Objekt byggs via EvidenceEngine,
    som laddar source_ref/version_ref från registret; utan referenser avvisas
    konstruktionen (regel 1 och 3).
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    evidence_id: str = Field(..., min_length=1, description="Unikt deterministiskt evidens-ID.")
    source_id: str = Field(..., min_length=1, description="Källa som evidensen pekar på.")
    source_version: str = Field(
        ..., min_length=1, description="Exakt källversion: 'source_id/version'."
    )
    locator: str = Field(
        ..., min_length=1, description="Beständig locator (AFS+kapitel+paragraf+stycke)."
    )
    claim_supported: str = Field(..., min_length=1, description="Vilket påstående som stöds.")
    quote_or_excerpt: str | None = Field(
        None, description="Utdrag/textreferens om tillgänglig (räcker ensamt ej för VERIFIED)."
    )
    source_type: SourceType | None = Field(None, description="Källtyp hämtad från källregistret.")
    authority_level: AuthorityLevel | None = Field(
        None, description="Auktoritetsnivå 1-4 hämtad från källregistret."
    )
    effective_date: date | None = Field(None, description="Giltighetsdatum för påståendet.")
    retrieved_at: datetime | None = Field(None, description="Hämtningstidpunkt för texten.")
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="Konfidens 0-1.")
    limitations: str | None = Field(None, description="Begränsningar och osäkerheter.")
    status: EvidenceStatus = Field(
        EvidenceStatus.UNVERIFIED, description="Sätts av Evidence Engine (§6), aldrig av agent."
    )
    source_ref: Source | None = Field(None, exclude=True, description="Laddad Source (spårbarhet).")
    version_ref: SourceVersion | None = Field(
        None, exclude=True, description="Laddad exakt SourceVersion (spårbarhet)."
    )

    @field_validator("evidence_id", "source_id", "source_version", "locator", "claim_supported")
    @classmethod
    def _no_whitespace_only(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("fält får inte vara blankt")
        return v.strip()

    @field_validator("locator")
    @classmethod
    def _validate_locator(cls, v: str) -> str:
        """Locator måste peka på en exakt nivå (minst en siffra)."""
        if not any(c.isdigit() for c in v):
            raise ValueError("locator måste innehålla minst ett siffervärde (t.ex. 2023:1)")
        return v

    @field_validator("source_version")
    @classmethod
    def _validate_source_version_format(cls, v: str) -> str:
        if "/" not in v:
            raise ValueError("source_version måste vara 'source_id/version'")
        return v

    @model_validator(mode="after")
    def _validate_traceability_and_status(self) -> "Evidence":
        # Regel 8: spårbarhet kräver laddade referenser (bygg via EvidenceEngine).
        if self.source_ref is None or self.version_ref is None:
            raise ValueError("source_ref och version_ref krävs; bygg evidens via EvidenceEngine")
        if self.source_ref.source_id != self.source_id:
            raise ValueError("source_ref matchar inte source_id")
        # Exakt källversion: "source_id/version" ska peka på version_ref.
        sid, sep, ver = self.source_version.partition("/")
        if not sep or sid != self.source_id or ver != self.version_ref.version:
            raise ValueError("source_version pekar inte på den exakta källversionen")
        if self.version_ref.source_id != self.source_id:
            raise ValueError("version_ref matchar inte source_id")
        # Regel 4+5: VERIFIED kräver arkitekturens verifieringskrav (§6).
        if self.status is EvidenceStatus.VERIFIED:
            if self.authority_level not in (
                AuthorityLevel.PRIMAR_LAG,
                AuthorityLevel.SECUNDAR_LAG,
            ):
                raise ValueError("VERIFIED kräver nivå-1/2-källa")
            if self.source_ref.version_status is not Currentness.CURRENT:
                raise ValueError("VERIFIED kräver aktuell (current) källa")
            if self.version_ref.superseded_by is not None:
                raise ValueError("VERIFIED får inte peka på en ersatt version")
            if self.retrieved_at is None:
                raise ValueError("VERIFIED kräver retrieved_at (texten måste vara hämtad)")
            if self.quote_or_excerpt is None:
                raise ValueError("VERIFIED kräver quote_or_excerpt (textstöd)")
            if self.effective_date is None:
                raise ValueError("VERIFIED kräver effective_date")
            if self.version_ref.snapshot_ref is None:
                raise ValueError("VERIFIED kräver snapshot_ref (hämtad mot snapshot)")
        # Regel 2: historik måste peka på ersatt/avslutad version.
        if self.status is EvidenceStatus.HISTORICAL:
            historical = (
                self.version_ref.superseded_by is not None
                or self.source_ref.version_status is Currentness.HISTORICAL
                or self.version_ref.effective_to is not None
            )
            if not historical:
                raise ValueError("HISTORICAL kräver ersatt/avslutad källversion")
        # Regel 6: konflikt måste beskrivas, aldrig tyst.
        if self.status is EvidenceStatus.CONFLICTING and not self.limitations:
            raise ValueError("CONFLICTING kräver limitations (beskriv konflikten)")
        return self

    # ------------------------------------------------------------------
    # Predikat
    # ------------------------------------------------------------------
    @property
    def is_verified(self) -> bool:
        return self.status is EvidenceStatus.VERIFIED

    @property
    def is_historical(self) -> bool:
        return self.status is EvidenceStatus.HISTORICAL

    @property
    def is_conflicting(self) -> bool:
        return self.status is EvidenceStatus.CONFLICTING

    # ------------------------------------------------------------------
    # Deterministisk serialisering (KMA-002-mönster)
    # ------------------------------------------------------------------
    def checksum(self) -> str:
        """SHA-256 över den deterministiska serialiseringen."""
        return compute_checksum(self.to_dict())

    def to_dict(self, *, include_none: bool = False) -> dict[str, Any]:
        """Deterministisk serialisering; None-fält filtreras som standard."""
        data = self.model_dump(mode="json", by_alias=True)
        if include_none:
            return data
        return {k: v for k, v in data.items() if v is not None}
