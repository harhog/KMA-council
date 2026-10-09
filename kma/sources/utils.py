"""KMA Council — Source Registry (KMA-002).

Deterministisk serialisering, checksumma och hjälparbete.
"""
import hashlib
import json
from datetime import date, datetime
from typing import Any

__all__ = [
    "compute_checksum",
    "deterministic_keys",
    "normalize_for_hash",
]


def _serialize(obj: Any) -> Any:
    """Serialisera ett objekt för deterministisk checksumma."""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in sorted(obj.items())}
    if hasattr(obj, "to_dict"):
        return _serialize(obj.to_dict())
    if hasattr(obj, "model_dump"):
        return _serialize(obj.model_dump(mode="json", by_alias=True))
    return str(obj)


def _jsonable(obj: Any) -> Any:
    """Konvertera objekt till JSON-säkert format (dict/list/str/...).

    Normaliseringen avser att vara version- och ordningsoberoende: hela
    trädet sorteras (dict-nycklar) och värden normaliseras i ordning.
    """
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, (list, tuple)):
        return [_jsonable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in sorted(obj.items())}
    if hasattr(obj, "to_dict"):
        return _jsonable(obj.to_dict())
    if hasattr(obj, "model_dump"):
        return _jsonable(obj.model_dump(mode="json", by_alias=True))
    return str(obj)


def normalize_for_hash(obj: Any) -> str:
    """Normera objekt för checksumma (versalfritt och sorterat).

    Produkten är ett JSON-serialiserat objekt med sorterade nycklar, så
    att typically samma objekt alltid ger samma hash oavsett fälts
    ordning.
    """
    jsonable = _jsonable(obj)
    return json.dumps(jsonable, sort_keys=True, separators=(",", ":"))


def compute_checksum(obj: Any, algorithm: str = "sha256") -> str:
    """Beräkna en checksumma för ett objekt (källtext, dict, modell, ...).

    Värdenas ordning påverkar inte resultatet: allt serialiseras
    deterministiskt och sorteras innan hashing.
    """
    data = normalize_for_hash(obj).encode("utf-8")
    if algorithm == "sha256":
        return hashlib.sha256(data).hexdigest()
    if algorithm == "md5":
        return hashlib.md5(data).hexdigest()
    raise ValueError(f"Okänd algoritm: {algorithm}")
    raise ValueError(f"Okänd algoritm: {algorithm}")


def deterministic_keys(d: dict) -> dict:
    """Returnera en kopia av dict med deterministisk nyckelordning."""
    return {k: d[k] for k in sorted(d.keys())}


def now_iso() -> str:
    """ISO-8601-tidsstämpel med lokaltid (valfri, deterministisk vid given tid)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")
