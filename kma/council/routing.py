"""KMA Council — Council Orchestration, deterministisk routing (KMA-005).

Route-tabell fran Notion sida 04 (KMA-005). Minsta tillrackliga rad per
fraga; okand fraga eskalerar, gissas aldrig (AD-4).
"""
from __future__ import annotations

from .errors import RoutingError
from .models import Question, QuestionKind

__all__ = [
    "ROUTE_TABLE",
    "FULL_COUNCIL",
    "route",
]

FULL_COUNCIL = (
    "CHAIR", "AFS", "SAM", "OSA", "BYGG",
    "RISK", "PRAKTIK", "REVISION", "REDTEAM", "RESEARCH",
)

# Notion sida 04 route-tabell. CHAIR orkestrerar alltid; listad separat i
# pipeline-stegen. REDTEAM/REVISION tillkommer fore syntes (arkitektur §5).
ROUTE_TABLE: dict[QuestionKind, tuple[str, ...]] = {
    QuestionKind.AFS_FRAGA: ("AFS", "RESEARCH"),
    QuestionKind.SAM: ("SAM", "AFS", "RESEARCH"),
    QuestionKind.OSA: ("OSA", "SAM", "RESEARCH"),
    QuestionKind.BYGG: ("BYGG", "AFS", "SAM", "RISK", "RESEARCH"),
    QuestionKind.INCIDENT: ("RISK", "SAM", "REVISION", "RESEARCH"),
    QuestionKind.FULL_REVIEW: FULL_COUNCIL,
}


def route(question: Question) -> tuple[str, ...]:
    """Returnera minsta tillrackliga rad for fragan.

    route_hint (valfri, fran intake) filtrerar raden till de hintade
    agenterna; okanda ID:n i hinten ger RoutingError. UNKNOWN utan giltig
    hint eskalerar med RoutingError — aldrig en gissad route.
    """
    members = ROUTE_TABLE.get(question.kind)
    if members is None or question.kind is QuestionKind.UNKNOWN:
        if question.route_hint:
            unknown = [h for h in question.route_hint if h not in FULL_COUNCIL]
            if unknown:
                raise RoutingError(f"okand agent i route_hint: {unknown}")
            if "CHAIR" in question.route_hint and len(question.route_hint) == 1:
                raise RoutingError("route_hint maste innehalla minst en expert utover CHAIR")
            return tuple(dict.fromkeys(question.route_hint))
        raise RoutingError(
            f"okand fragakategori ({question.kind.value}); eskalera till manuell bedomning"
        )
    if question.route_hint:
        unknown = [h for h in question.route_hint if h not in FULL_COUNCIL]
        if unknown:
            raise RoutingError(f"okand agent i route_hint: {unknown}")
        hinted = [m for m in members if m in question.route_hint]
        if not hinted:
            raise RoutingError("route_hint matchar ingen agent i route-tabellen")
        return tuple(hinted)
    return members
