"""KMA Council — Source Registry (KMA-002).

Enkel, deterministisk och testbar registermodell för regulatoriska källor.
Följer domänmodellen i docs/KMA_ARCHITECTURE.md §4.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = [
    "AuthorityLevel",
    "Currentness",
    "Source",
    "SourceType",
    "SourceVersion",
]


class AuthorityLevel(str, Enum):
    """Auktoritetsnivå för regulatorisk källa (1 = högst auktoritet).

    KMA-002 regler: nivå 1/2 (primär/sekundär officiell) väger tyngre än
    nivå 4. Sekundära källor får aldrig ensam bära ett regleringspåstående.
    """

    PRIMAR_LAG = "level_1"
    SECUNDAR_LAG = "level_2"
    ALLMANNAT_RAD = "level_3"
    SEKUNDAR_SPECIALIST = "level_4"


class Currentness(str, Enum):
    """Currentness/status för en källa.

    - current:    Gäller just nu (konsoliderad aktuell version).
    - historical: Gällde tidigare, ersatt.
    - unknown:    Aktuellhet ej verifierad (t.ex. registration före first-hit).
    """

    CURRENT = "current"
    HISTORICAL = "historical"
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    """Källmode för regulatoriska källor."""

    AFS = "AFS"
    LAG = "Lag"
    FORORDNING = "Förordning"
    ALLMANNAT_RAD = "Allmänt råd"
    VAGLEDNING = "Vägledning"
    BRANSCHRAD = "Branschråd"
    ANNAN = "Annan"

class Source(BaseModel):
    """Registerpost för en regulatorisk källa (KMA_ARCHITECTURE.md §4)."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    source_id: str = Field(..., min_length=1, description="Unikt källmärke (t.ex. AFS2023:1).")
    publisher: str = Field(..., min_length=1, description="Utgivare, t.ex. Arbetsmiljöverket.")
    title: str = Field(..., min_length=1, description="Källtitel.")
    source_type: SourceType = Field(..., description="Källmode från SourceType.")
    canonical_url: str = Field(..., min_length=1, description="Officiell primär-URL.")
    jurisdiction: str = Field("SE", min_length=1, description="Jurisdiktion, t.ex. SE, EU.")
    authority_level: AuthorityLevel = Field(
        AuthorityLevel.SEKUNDAR_SPECIALIST,
        description="Auktoritetsnivå 1–4. 1 = primär lag.",
    )
    effective_from: date | None = Field(None, description="Gäller från (inklusive).")
    effective_to: date | None = Field(None, description="Gäller tills (inklusive).")
    retrieved_at: datetime | None = Field(
        None, description="När källan hämtades/kontrollerades."
    )
    version_status: Currentness = Field(
        Currentness.UNKNOWN, description="current / historical / unknown."
    )
    checksum: str | None = Field(
        None, description="SHA-256 hex digest av konsoliderad text (valfritt)."
    )
    amended_from_source_id: str | None = Field(
        None, description="Källa som denna är en ändring av."
    )
    consolidated: bool = Field(
        False, description="Källa är en konsoliderad version (kombinera flera)."
    )
    topics: list[str] = Field(
        default_factory=list, description="Teman/kategorier (ej auktoritativa)."
    )

    # ------------------------------------------------------------------
    # Validering
    # ------------------------------------------------------------------
    @field_validator("source_id", "publisher", "title", "canonical_url", "jurisdiction")
    @classmethod
    def _no_whitespace_only(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("fält får inte vara blankt")
        return v.strip()

    @field_validator("canonical_url")
    @classmethod
    def _validate_canonical_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                "canonical_url måste börja med http:// eller https://"
            )
        return v

    @field_validator("topics", mode="before")
    @classmethod
    def _normalize_topics(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        if isinstance(v, (list, tuple)):
            return [str(t).strip() for t in v if str(t).strip()]
        return list(v)

    @model_validator(mode="after")
    def _validate_effective_dates(self) -> "Source":
        if self.effective_from is not None and self.effective_to is not None:
            if self.effective_from > self.effective_to:
                raise ValueError(
                    "effective_from kan inte vara senare än effective_to"
                )
        return self

    # ------------------------------------------------------------------
    # Currentness-predikat (beteende, ej bara instansiering)
    # ------------------------------------------------------------------
    @property
    def is_current(self) -> bool:
        return self.version_status is Currentness.CURRENT

    @property
    def is_historical(self) -> bool:
        return self.version_status is Currentness.HISTORICAL

    @property
    def is_unknown(self) -> bool:
        return self.version_status is Currentness.UNKNOWN

    # ------------------------------------------------------------------
    # Serialisering
    # ------------------------------------------------------------------
    def to_dict(self, *, include_none: bool = False) -> dict:
        """Deterministisk serialisering.

        model_dump() ger redan en stabil ordning. None-fält filtreras.
        """
        data = self.model_dump(mode="json", by_alias=True)
        if include_none:
            return data
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "Source":
        return cls.model_validate(data)


__all__ = [
    "AuthorityLevel",
    "Currentness",
    "Source",
    "SourceType",
    "SourceVersion",
]

class SourceVersion(BaseModel):
    """Versions- och amandehistoriknivå (KMA-002 krav 2 + KMA_ARCHITECTURE.md §4)."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    source_id: str = Field(..., min_length=1, description="Källan för versionen.")
    version: str = Field(..., min_length=1, description="Versionssträng, t.ex. '2023:1'.")
    effective_from: date | None = Field(None, description="Gäller från.")
    effective_to: date | None = Field(None, description="Gäller tills.")
    amendment_history: list[str] = Field(
        default_factory=list, description="Historik över ändringar."
    )
    consolidated: bool = Field(
        False, description="Konsoliderad version (kombinerar delversioner)."
    )
    supersedes: str | None = Field(
        None, description="Versions ID som denna ersätter."
    )
    superseded_by: str | None = Field(
        None, description="Versions ID som denna ersätts av."
    )
    snapshot_ref: str | None = Field(
        None, description="Referens till snapshot (t.ex. 'data/snapshots/2026-01-05')."
    )

    @field_validator("source_id", "version")
    @classmethod
    def _no_whitespace_only(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("fält får inte vara blankt")
        return v.strip()

    @model_validator(mode="after")
    def _validate_version_dates(self) -> "SourceVersion":
        if self.effective_from is not None and self.effective_to is not None:
            if self.effective_from > self.effective_to:
                raise ValueError(
                    "effective_from kan inte vara senare än effective_to"
                )
        return self

    def is_consolidated(self) -> bool:
        return self.consolidated

    def is_future_version(self) -> bool:
        """Kommande ändring → effektivt tills datum > dagens datum."""
        if self.effective_to is not None and self.effective_to > date.today():
            return True
        return False

    def to_dict(self, *, include_none: bool = False) -> dict:
        data = self.model_dump(mode="json", by_alias=True)
        if include_none:
            return data
        return {k: v for k, v in data.items() if v is not None}


