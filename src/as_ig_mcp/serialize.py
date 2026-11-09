"""Turn instagrapi objects into plain JSON-serialisable data."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def plain(obj: Any) -> Any:
    """Return ``obj`` as data that ``json.dumps`` can encode.

    Pydantic models are dumped, datetimes become ISO 8601 strings, lists and
    tuples are mapped, dictionaries are mapped value by value, and anything
    else is stringified.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (list, tuple, set)):
        return [plain(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): plain(value) for key, value in obj.items()}
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        return plain(dump())
    return str(obj)


def plain_list(items: Any, limit: int | None = None) -> list[Any]:
    """``plain`` over every item in ``items``, truncated to ``limit``."""
    if items is None:
        return []
    result = [plain(item) for item in items]
    if limit is not None and limit >= 0:
        return result[:limit]
    return result
