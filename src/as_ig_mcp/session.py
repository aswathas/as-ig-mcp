"""DPAPI-encrypted session storage for AS-IG-MCP."""

from __future__ import annotations

import ctypes
import json
import re
from ctypes import wintypes
from typing import Any

from . import state

DEFAULT_ENTROPY = b"as-ig-mcp"
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class SessionError(Exception):
    """Raised when the stored session cannot be encrypted, decrypted or decoded."""


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


_crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_crypt32.CryptProtectData.argtypes = [
    ctypes.POINTER(_DATA_BLOB),
    wintypes.LPCWSTR,
    ctypes.POINTER(_DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(_DATA_BLOB),
]
_crypt32.CryptProtectData.restype = wintypes.BOOL

_crypt32.CryptUnprotectData.argtypes = [
    ctypes.POINTER(_DATA_BLOB),
    ctypes.POINTER(wintypes.LPWSTR),
    ctypes.POINTER(_DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(_DATA_BLOB),
]
_crypt32.CryptUnprotectData.restype = wintypes.BOOL

_kernel32.LocalFree.argtypes = [ctypes.c_void_p]
_kernel32.LocalFree.restype = ctypes.c_void_p


def _blob(data: bytes) -> tuple[_DATA_BLOB, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    blob = _DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    return blob, buffer


def _take_output(blob: _DATA_BLOB) -> bytes:
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        _kernel32.LocalFree(ctypes.cast(blob.pbData, ctypes.c_void_p))


def encrypt_bytes(data: bytes, entropy: bytes = DEFAULT_ENTROPY) -> bytes:
    """Encrypt bytes with DPAPI, bound to the current Windows user."""
    in_blob, in_buffer = _blob(data)
    entropy_blob, entropy_buffer = _blob(entropy)
    out_blob = _DATA_BLOB()
    ok = _crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "as-ig-mcp session",
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        error = ctypes.get_last_error()
        raise SessionError(
            f"CryptProtectData failed (WinError {error}); the session was not written"
        )
    return _take_output(out_blob)


def decrypt_bytes(blob: bytes, entropy: bytes = DEFAULT_ENTROPY) -> bytes:
    """Decrypt a DPAPI blob created for the current Windows user."""
    in_blob, in_buffer = _blob(blob)
    entropy_blob, entropy_buffer = _blob(entropy)
    out_blob = _DATA_BLOB()
    ok = _crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    )
    if not ok:
        error = ctypes.get_last_error()
        raise SessionError(
            "could not decrypt the session (wrong Windows user or corrupt file); "
            f"relogin with ig_session relogin (WinError {error})"
        )
    return _take_output(out_blob)


def save_session(settings: dict[str, Any]) -> None:
    payload = json.dumps(settings, ensure_ascii=False).encode("utf-8")
    state.atomic_write_bytes(state.session_path(), encrypt_bytes(payload))


def load_session() -> dict[str, Any] | None:
    path = state.session_path()
    if not path.exists():
        return None
    blob = path.read_bytes()
    try:
        return json.loads(decrypt_bytes(blob).decode("utf-8"))
    except (SessionError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        if isinstance(exc, SessionError):
            raise
        raise SessionError(
            "the session file is malformed; relogin with ig_session relogin"
        ) from exc


def clear_session() -> None:
    path = state.session_path()
    if path.exists():
        path.unlink()


_SESSIONID_PREFIX = re.compile(r"^(\d+)")


def settings_identity(settings: dict[str, Any] | None) -> dict[str, Any]:
    """Read username, user id and sessionid out of stored instagrapi settings."""
    if not settings:
        return {
            "present": False,
            "username": None,
            "user_id": None,
            "sessionid": None,
        }

    cookies = settings.get("cookies")
    authorization = settings.get("authorization_data")
    cookies = cookies if isinstance(cookies, dict) else {}
    authorization = authorization if isinstance(authorization, dict) else {}

    sessionid = cookies.get("sessionid") or authorization.get("sessionid")

    user_id = settings.get("user_id")
    if user_id is None:
        user_id = cookies.get("ds_user_id") or authorization.get("ds_user_id")
    if user_id is None and isinstance(sessionid, str):
        match = _SESSIONID_PREFIX.match(sessionid)
        if match:
            user_id = match.group(1)

    return {
        "present": True,
        "username": settings.get("username"),
        "user_id": str(user_id) if user_id is not None else None,
        "sessionid": sessionid,
    }
