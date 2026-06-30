import pytest

from observability.messaging import extract_context, inject_headers


@pytest.fixture(autouse=True)
def _otel_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")


def test_inject_preserves_custom_headers() -> None:
    headers = inject_headers({"request_id": "req_123", "chat_id": "chat_123"})
    assert headers["request_id"] == "req_123"
    assert headers["chat_id"] == "chat_123"


def test_extract_reads_w3c_traceparent() -> None:
    headers = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "request_id": "req_123",
    }
    context = extract_context(headers)
    assert context is not None
