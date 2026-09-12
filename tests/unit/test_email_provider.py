import pytest

from app.core.config import settings
from app.services.email_provider import BrevoEmailProvider, NoOpEmailProvider, get_email_provider


async def test_noop_provider_does_not_raise():
    await NoOpEmailProvider().send(to="a@example.com", subject="hi", text="hello")


def test_get_email_provider_defaults_to_noop(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "none")
    assert isinstance(get_email_provider(), NoOpEmailProvider)


def test_get_email_provider_returns_brevo_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "email_provider", "brevo")
    monkeypatch.setattr(settings, "brevo_api_key", "test-key")
    assert isinstance(get_email_provider(), BrevoEmailProvider)


def test_brevo_provider_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "brevo_api_key", "")
    with pytest.raises(RuntimeError):
        BrevoEmailProvider()


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse, captured: dict) -> None:
        self._response = response
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json, headers):
        self._captured["url"] = url
        self._captured["json"] = json
        self._captured["headers"] = headers
        return self._response


async def test_brevo_provider_sends_via_http_api(monkeypatch):
    monkeypatch.setattr(settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(settings, "email_from_address", "no-reply@example.com")
    monkeypatch.setattr(settings, "email_from_name", "Test Gym")

    captured: dict = {}
    monkeypatch.setattr(
        "app.services.email_provider.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(_FakeResponse(201), captured),
    )

    await BrevoEmailProvider().send(to="user@example.com", subject="Reset", text="code: abc123")

    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["json"]["to"] == [{"email": "user@example.com"}]
    assert captured["json"]["sender"] == {"email": "no-reply@example.com", "name": "Test Gym"}
    assert captured["headers"]["api-key"] == "test-key"


async def test_brevo_provider_raises_on_error_status(monkeypatch):
    monkeypatch.setattr(settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(
        "app.services.email_provider.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(_FakeResponse(400, "bad request"), {}),
    )

    with pytest.raises(RuntimeError):
        await BrevoEmailProvider().send(to="user@example.com", subject="Reset", text="code")
