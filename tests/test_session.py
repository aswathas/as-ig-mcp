"""Offline tests for DPAPI session storage."""

import pytest

from as_ig_mcp import session, state


def test_encrypt_then_decrypt_round_trip():
    payload = b'{"user_id": "42", "sessionid": "not-a-real-session"}'
    blob = session.encrypt_bytes(payload)
    assert blob != payload
    assert session.decrypt_bytes(blob) == payload


def test_decrypting_a_corrupted_blob_raises_session_error():
    with pytest.raises(session.SessionError):
        session.decrypt_bytes(b"this is not a DPAPI blob")


def test_save_then_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    settings = {"user_id": "42", "sessionid": "not-a-real-session", "uuids": {}}
    session.save_session(settings)
    assert state.session_path().exists()
    assert session.load_session() == settings


def test_load_missing_session_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert session.load_session() is None


def test_clear_session_removes_the_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    session.save_session({"user_id": "42"})
    path = state.session_path()
    assert path.exists()
    session.clear_session()
    assert not path.exists()
