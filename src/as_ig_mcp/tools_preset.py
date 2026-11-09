"""ig_preset: saved caption, hashtag, first-comment and DM-reply templates."""

from __future__ import annotations

from typing import Any

from .presets import PRESET_KINDS, PresetError, PresetStore

ACTIONS = ("list", "get", "set", "delete")


def ig_preset(
    action: str = "list",
    name: str | None = None,
    content: str | None = None,
    kind: str = "caption",
) -> dict[str, Any]:
    """List, read, save or remove one local text preset."""
    name_action = str(action or "list").strip().lower()
    store = PresetStore()

    try:
        if name_action == "list":
            return {"ok": True, "presets": store.list()}
        if name_action == "get":
            preset = store.get(name)
            if preset is None:
                return {"ok": False, "error": f"no preset named {name!r}"}
            return {"ok": True, "preset": preset}
        if name_action == "set":
            preset = store.set(name=name, kind=kind, content=content)
            return {"ok": True, "preset": preset}
        if name_action == "delete":
            removed = store.delete(name)
            result: dict[str, Any] = {"ok": True, "deleted": name, "existed": removed}
            if not removed:
                result["message"] = f"no preset named {name!r}"
            return result
    except PresetError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    return {
        "ok": False,
        "error": f"unknown action: {name_action!r}; valid: {', '.join(ACTIONS)}",
        "kinds": list(PRESET_KINDS),
    }
