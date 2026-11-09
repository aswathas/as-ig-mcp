"""DPAPI-encrypted session storage and the password login flow."""

from __future__ import annotations

import ctypes
import getpass
import json
import re
from ctypes import wintypes
from typing import Any, Callable

from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired

from . import state

DEFAULT_ENTROPY = b"as-ig-mcp"
CRYPTPROTECT_UI_FORBIDDEN = 0x1
SOURCE_KEY = "_as_ig_source"


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


def save_session(settings: dict[str, Any], source: str | None = None) -> None:
    values = dict(settings)
    if source:
        values[SOURCE_KEY] = source
    payload = json.dumps(values, ensure_ascii=False).encode("utf-8")
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


def session_source(settings: dict[str, Any] | None) -> str:
    """How the stored session was created: the password flow or a file import."""
    if not settings:
        return "none"
    source = settings.get(SOURCE_KEY)
    return str(source) if source else "file"


def _scrub(text: Any, password: str) -> str:
    message = str(text)
    if password:
        message = message.replace(password, "<redacted>")
    return message


def login_with_password(
    *,
    username: str | None = None,
    password: str | None = None,
    relogin: bool = False,
    client_factory: Callable[[], Any] | None = None,
    ask_username: Callable[[str], str] | None = None,
    ask_password: Callable[[str], str] | None = None,
    ask_code: Callable[[str], str] | None = None,
    emit: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Log in with the account password and save the resulting session.

    The password is read from a no-echo prompt (``getpass``) and is never
    printed, stored or logged. When Instagram asks for a two-factor or email
    code, the prompt asks for it once and retries the login exactly once.
    """
    ask_username = ask_username or (lambda prompt: input(prompt))
    ask_password = ask_password or getpass.getpass
    ask_code = ask_code or (lambda prompt: input(prompt))
    emit = emit or print
    factory = client_factory or Client

    if username is None:
        username = str(ask_username("Instagram username: ")).strip()
    if not username:
        return {"ok": False, "error": "no username given"}

    if password is None:
        password = ask_password("Instagram password: ")
    if not password:
        return {"ok": False, "error": "no password given"}

    platform = factory()
    try:
        platform.login(username, password, relogin=relogin)
    except TwoFactorRequired:
        emit("enter the code from the email or the app:")
        code = str(ask_code("Verification code: ")).strip()
        if not code:
            return {"ok": False, "error": "a verification code is required to finish login"}
        try:
            platform.login(username, password, verification_code=code)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            return {"ok": False, "error": _scrub(message, password)}
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        return {"ok": False, "error": _scrub(message, password)}

    settings = platform.get_settings()
    if not isinstance(settings, dict):
        return {"ok": False, "error": "Instagram did not return session settings"}
    settings = dict(settings)
    settings.setdefault("username", username)
    try:
        save_session(settings, source="password")
    except Exception as exc:
        return {"ok": False, "error": _scrub(f"{type(exc).__name__}: {exc}", password)}

    identity = settings_identity(settings)
    return {
        "ok": True,
        "username": identity["username"],
        "user_id": identity["user_id"],
    }


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
