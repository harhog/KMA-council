"""KMA Council — Evidence Engine (KMA-003).

Anpassade felklasser för evidence-validation och gate-logik.
"""
from __future__ import annotations

__all__ = [
    "EvidenceValidationError",
    "UnknownSourceError",
    "UnknownSourceVersionError",
    "VerificationError",
]


class EvidenceValidationError(ValueError):
    """Valideringsfel för ett Evidence-objekt (obligatorisk metadata saknas)."""


class UnknownSourceError(EvidenceValidationError):
    """Evidensen refererar till en okänd (oregistrerad) källa."""


class UnknownSourceVersionError(EvidenceValidationError):
    """Evidensen refererar till en okänd källversion."""


class VerificationError(EvidenceValidationError):
    """Ett verifieringskrav för VERIFIED var uppfyllt i otillåten läge."""
