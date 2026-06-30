import pytest


@pytest.fixture(autouse=True)
def _disable_otel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
