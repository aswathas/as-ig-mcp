"""Offline tests for the password login and relogin flow."""

from __future__ import annotations

from typing import Any

from instagrapi.exceptions import BadPassword, TwoFactorRequired

from as_ig_mcp import session, tools_session


class FakeLoginClient:
    """A fake instagrapi client: no network, records what login received."""

    def __init__(self, *, two_factor: bool = False, bad_password: bool = False) -> None:
        self.two_factor = two_factor
        self.bad_password = bad_password
        self.calls: list[dict[str, Any]] = []
        self.settings = {
            "username": "my_biz_account",
            "cookies": {
                "sessionid": "42_not-a-real-session",
                "csrftoken": "not-a-real-csrf",
                "ds_user_id": "42",
            },
            "authorization_data": {"ds_user_id": "42", "sessionid": "42_not-a-real-session"},
        }

    def login(
        self,
        username: str,
        password: str,
        relogin: bool = False,
        verification_code: str = "",
    ) -> bool:
        self.calls.append(
            {
                "username": username,
                "password": password,
                "relogin": relogin,
                "verification_code": verification_code,
            }
        )
        if self.bad_password:
            raise BadPassword("The password you entered is incorrect")
        if self.two_factor and not verification_code:
            raise TwoFactorRequired("two-factor required")
        return True

    def get_settings(self) -> dict[str, Any]:
        return self.settings


def _run(monkeypatch, tmp_path, client: FakeLoginClient, **overrides):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    output: list[str] = []
    result = session.login_with_password(
        username="my_biz_account",
        password="hunter2-secret",
        client_factory=lambda: client,
        ask_code=lambda prompt: "123456",
        emit=output.append,
        **overrides,
    )
    return result, output


def test_two_factor_code_is_asked_for_and_used_once(tmp_path, monkeypatch):
    fake = FakeLoginClient(two_factor=True)
    result, output = _run(monkeypatch, tmp_path, fake)

    assert result["ok"] is True
    assert result["username"] == "my_biz_account"
    assert result["user_id"] == "42"

    assert len(fake.calls) == 2
    assert fake.calls[0]["verification_code"] == ""
    assert fake.calls[1]["verification_code"] == "123456"
    assert "enter the code from the email or the app:" in output

    stored = session.load_session()
    assert stored is not None
    assert session.session_source(stored) == "password"


def test_wrong_password_returns_an_error(tmp_path, monkeypatch):
    fake = FakeLoginClient(bad_password=True)
    result, _output = _run(monkeypatch, tmp_path, fake)

    assert result["ok"] is False
    assert "error" in result
    assert session.load_session() is None


def test_the_password_never_appears_in_the_output(tmp_path, monkeypatch):
    fake = FakeLoginClient(two_factor=True)
    result, output = _run(monkeypatch, tmp_path, fake)

    printed = "\n".join(output)
    assert "hunter2-secret" not in printed
    assert "hunter2-secret" not in result.get("error", "")


def test_the_password_never_appears_in_an_error(tmp_path, monkeypatch):
    fake = FakeLoginClient(bad_password=True)
    result, output = _run(monkeypatch, tmp_path, fake)

    assert "hunter2-secret" not in "\n".join(output)
    assert "hunter2-secret" not in result["error"]


def test_relogin_replaces_the_stored_session(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    session.save_session({"user_id": "1", "cookies": {"sessionid": "1_old"}}, source="file")

    fake = FakeLoginClient()
    result = session.login_with_password(
        username="my_biz_account",
        password="hunter2-secret",
        relogin=True,
        client_factory=lambda: fake,
        emit=lambda _line: None,
    )

    assert result["ok"] is True
    assert fake.calls[0]["relogin"] is True
    stored = session.load_session()
    assert stored is not None
    assert session.session_source(stored) == "password"
    assert stored["cookies"]["ds_user_id"] == "42"


def test_mcp_relogin_points_at_the_terminal_command(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    result = tools_session.ig_session("relogin")

    assert result["ok"] is False
    assert "python -m as_ig_mcp session relogin" in result["error"]
    assert result["command"] == "python -m as_ig_mcp session relogin"


def test_status_reports_the_password_source(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    fake = FakeLoginClient()
    session.login_with_password(
        username="my_biz_account",
        password="hunter2-secret",
        client_factory=lambda: fake,
        emit=lambda _line: None,
    )

    status = tools_session.ig_session("status")

    assert status["ok"] is True
    assert status["session"]["present"] is True
    assert status["session"]["source"] == "password"
