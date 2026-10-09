"""KMA Council — Evidence Engine (KMA-003).

Deterministisk evidence gate: representerar, validerar och spårar evidens
för påståenden om KMA-regler. Ingen LLM, inget RAG, inga externa beroenden
(arkitektur AD-1 och AD-4). Status sätts alltid av gaten, aldrig av indata.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from kma.sources import (
    AuthorityLevel,
    Currentness,
    Source,
    SourceRegistry,
    SourceVersion,
)
from kma.sources.utils import compute_checksum

from .errors import EvidenceValidationError, UnknownSourceError, UnknownSourceVersionError
from .models import Evidence, EvidenceStatus

__all__ = ["EvidenceConflict", "EvidenceEngine"]


@dataclass(frozen=True)
class EvidenceConflict:
    """Motstridig evidens för samma påstående — båda sidor bevarade (regel 6).

    resolved är alltid False: konflikten löses aldrig tyst i detta lager.
    """

    claim_supported: str
    evidence_ids: tuple[str, ...]
    statuses: tuple[EvidenceStatus, ...]

    @property
    def resolved(self) -> bool:
        return False


class EvidenceEngine:
    """Deterministisk evidence gate (KMA-003, arkitektur §6).

    - build() har inget status-parameter: VERIFIED kan inte sättas via indata.
    - verify_claim() ärv status från svagaste evidensen (§4):
      VERIFIED < PARTIALLY_VERIFIED < UNVERIFIED < HISTORICAL < CONFLICTING.
    - Källa och exakt version hämtas alltid ur registret (regel 1 och 8).
    """

    _SEVERITY = {
        EvidenceStatus.VERIFIED: 0,
        EvidenceStatus.PARTIALLY_VERIFIED: 1,
        EvidenceStatus.UNVERIFIED: 2,
        EvidenceStatus.HISTORICAL: 3,
        EvidenceStatus.CONFLICTING: 4,
    }

    def __init__(self, registry: SourceRegistry, versions: Sequence[SourceVersion] = ()) -> None:
        self._registry = registry
        self._versions: dict[tuple[str, str], SourceVersion] = {}
        for version in versions:
            self.register_version(version)

    # ------------------------------------------------------------------
    # Registrering
    # ------------------------------------------------------------------
    def register_version(self, version: SourceVersion) -> SourceVersion:
        """Registrera en exakt källversion. Källan måste finnas i registret."""
        if not self._registry.has(version.source_id):
            raise UnknownSourceError(
                f"versionens källa '{version.source_id}' är inte registrerad"
            )
        key = (version.source_id, version.version)
        if key in self._versions:
            raise EvidenceValidationError(
                f"källversion '{version.source_id}/{version.version}' är redan registrerad"
            )
        self._versions[key] = version
        return version

    # ------------------------------------------------------------------
    # Deterministisk identitet
    # ------------------------------------------------------------------
    @staticmethod
    def make_evidence_id(source_id: str, source_version: str, locator: str,
                         claim_supported: str) -> str:
        """Stabilt evidens-ID: samma indata ger alltid samma ID."""
        digest = compute_checksum(
            {
                "claim": claim_supported,
                "locator": locator,
                "source": source_id,
                "version": source_version,
            }
        )
        return f"EV-{digest[:16]}"

    # ------------------------------------------------------------------
    # Bygg evidens (enda vägen till ett Evidence-objekt)
    # ------------------------------------------------------------------
    def build(
        self,
        *,
        source_id: str,
        version: str,
        locator: str,
        claim_supported: str,
        as_of: date | None = None,
        effective_date: date | None = None,
        retrieved_at=None,
        quote_or_excerpt: str | None = None,
        confidence: float | None = None,
        limitations: str | None = None,
        evidence_id: str | None = None,
    ) -> Evidence:
        """Bygg evidens mot registret. Status beräknas av gaten — aldrig av indata.

        Okänd källa → UnknownSourceError; okänd källversion →
        UnknownSourceVersionError (regel 1). Att skicka status som keyword
        argument ger TypeError (regel 5).
        """
        as_of = as_of or date.today()
        source = self._registry.get(source_id)
        if source is None:
            raise UnknownSourceError(f"okänd källa: {source_id}")
        source_version = self._versions.get((source_id, version))
        if source_version is None:
            raise UnknownSourceVersionError(f"okänd källversion: {source_id}/{version}")

        status, _reason = self._evaluate(
            source,
            source_version,
            as_of=as_of,
            effective_date=effective_date,
            retrieved_at=retrieved_at,
            quote_or_excerpt=quote_or_excerpt,
        )
        full_version = f"{source_id}/{version}"
        return Evidence(
            evidence_id=evidence_id
            or self.make_evidence_id(source_id, full_version, locator, claim_supported),
            source_id=source_id,
            source_version=full_version,
            locator=locator,
            claim_supported=claim_supported,
            quote_or_excerpt=quote_or_excerpt,
            source_type=source.source_type,
            authority_level=source.authority_level,
            effective_date=effective_date,
            retrieved_at=retrieved_at,
            confidence=confidence,
            limitations=limitations,
            status=status,
            source_ref=source,
            version_ref=source_version,
        )

    # ------------------------------------------------------------------
    # Gate (deterministisk kod, arkitektur §6)
    # ------------------------------------------------------------------
    def _evaluate(
        self,
        source: Source,
        version: SourceVersion,
        *,
        as_of: date,
        effective_date: date | None,
        retrieved_at,
        quote_or_excerpt: str | None,
    ) -> tuple[EvidenceStatus, str]:
        # 1) Historik före allt annat — får aldrig presenteras som aktuell (regel 2).
        if source.version_status is Currentness.HISTORICAL:
            return EvidenceStatus.HISTORICAL, "källans versionstatus är historical"
        if version.superseded_by is not None:
            return EvidenceStatus.HISTORICAL, f"version ersatt av {version.superseded_by}"
        if version.effective_to is not None and as_of > version.effective_to:
            return EvidenceStatus.HISTORICAL, f"version utgången {version.effective_to}"
        # 2) Okänd aktuell status → osäker, aldrig VERIFIED.
        if source.version_status is Currentness.UNKNOWN:
            return EvidenceStatus.UNVERIFIED, "okänd aktuell status (currentness ej verifierad)"
        # 3) Framtida ikraftträdande → gäller ännu inte.
        if version.effective_from is not None and as_of < version.effective_from:
            return EvidenceStatus.UNVERIFIED, f"framtida ikraftträdande {version.effective_from}"
        # 4) Auktoritetsnivå (AD-2): nivå 4 bär aldrig ensam regelclaim.
        if source.authority_level is AuthorityLevel.SEKUNDAR_SPECIALIST:
            return EvidenceStatus.UNVERIFIED, "nivå-4 bär aldrig regulatoriskt påstående ensam"
        if source.authority_level is AuthorityLevel.ALLMANNAT_RAD:
            return EvidenceStatus.PARTIALLY_VERIFIED, "nivå-3 bär ej föreskriftstext"
        # 5) Registrerad ≠ hämtad ≠ stödd (regel 9).
        if retrieved_at is None:
            return EvidenceStatus.UNVERIFIED, "text ej hämtad (retrieved_at saknas)"
        if quote_or_excerpt is None:
            return EvidenceStatus.PARTIALLY_VERIFIED, "textreferens saknas (quote_or_excerpt)"
        if effective_date is None:
            return EvidenceStatus.PARTIALLY_VERIFIED, "giltighetsdatum saknas (effective_date)"
        if version.effective_from is not None and effective_date < version.effective_from:
            return EvidenceStatus.PARTIALLY_VERIFIED, "giltighetsdatum före versionens ikraftträdande"
        if version.effective_to is not None and effective_date > version.effective_to:
            return EvidenceStatus.PARTIALLY_VERIFIED, "giltighetsdatum efter versionens slut"
        if version.snapshot_ref is None:
            return EvidenceStatus.PARTIALLY_VERIFIED, "snapshot saknas (ej hämtad mot snapshot)"
        # Samtliga krav i §6 uppfyllda: nivå-1/2, aktuell version, exakt locator.
        return EvidenceStatus.VERIFIED, "nivå-1/2, aktuell version, exakt locator, hämtad text"

    # ------------------------------------------------------------------
    # Spårbarhet (regel 8)
    # ------------------------------------------------------------------
    def trace(self, evidence: Evidence) -> tuple[Source, SourceVersion]:
        """Resolv evidens till exakt källa och källversion via registret.

        Förlitar sig på lagrade ID:n (source_id + source_version), inte på
        källans aktuella status i efterhand.
        """
        source = self._registry.get(evidence.source_id)
        if source is None:
            raise UnknownSourceError(f"okänd källa: {evidence.source_id}")
        sid, _, ver = evidence.source_version.partition("/")
        source_version = self._versions.get((sid, ver))
        if source_version is None:
            raise UnknownSourceVersionError(
                f"okänd källversion: {evidence.source_version}"
            )
        return source, source_version

    # ------------------------------------------------------------------
    # Konflikter (regel 6) — representeras, löses aldrig tyst
    # ------------------------------------------------------------------
    def detect_conflicts(self, evidences: Iterable[Evidence]) -> list[EvidenceConflict]:
        """Flagga påståenden där evidenser har motstridiga gate-statusar.

        Inga evidenser ändras; konflikten redovisas med båda sidor (resolved=False).
        """
        groups: dict[str, list[Evidence]] = {}
        for item in evidences:
            groups.setdefault(item.claim_supported, []).append(item)

        conflicts: list[EvidenceConflict] = []
        for claim in sorted(groups):
            members = groups[claim]
            if len(members) < 2:
                continue
            statuses = tuple(m.status for m in members)
            if len(set(statuses)) > 1 or any(
                s is EvidenceStatus.CONFLICTING for s in statuses
            ):
                conflicts.append(
                    EvidenceConflict(
                        claim_supported=claim,
                        evidence_ids=tuple(m.evidence_id for m in members),
                        statuses=statuses,
                    )
                )
        return conflicts

    def mark_conflicting(self, evidence: Evidence, description: str) -> Evidence:
        """Returnera evidensen som CONFLICTING med obligatorisk beskrivning.

        Originalobjektet bevaras oförändrat; konflikten tystlys aldrig.
        """
        if not description or not description.strip():
            raise EvidenceValidationError("CONFLICTING kräver en beskrivning (limitations)")
        return Evidence(
            evidence_id=evidence.evidence_id,
            source_id=evidence.source_id,
            source_version=evidence.source_version,
            locator=evidence.locator,
            claim_supported=evidence.claim_supported,
            quote_or_excerpt=evidence.quote_or_excerpt,
            source_type=evidence.source_type,
            authority_level=evidence.authority_level,
            effective_date=evidence.effective_date,
            retrieved_at=evidence.retrieved_at,
            confidence=evidence.confidence,
            limitations=description,
            status=EvidenceStatus.CONFLICTING,
            source_ref=evidence.source_ref,
            version_ref=evidence.version_ref,
        )

    # ------------------------------------------------------------------
    # Påståendegate (§4: status ärvs från svagaste evidensen)
    # ------------------------------------------------------------------
    def verify_claim(self, evidences: Iterable[Evidence]) -> EvidenceStatus:
        """Påståendestatus = svagaste evidensens status.

        Tom evidensmängd → UNVERIFIED (aldrig VERIFIED utan evidens).
        """
        items = list(evidences)
        if not items:
            return EvidenceStatus.UNVERIFIED
        return max(items, key=lambda e: self._SEVERITY[e.status]).status
