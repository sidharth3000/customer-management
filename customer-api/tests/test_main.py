from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_check():
    """GET / should return 200 with status ok."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_lifespan_creates_and_disposes():
    """Lifespan should create tables on startup and dispose the engine on shutdown."""
    from tests.conftest import test_engine

    with patch("app.main.engine", test_engine):
        from app.main import lifespan

        async with lifespan(app):
            pass  # startup ran (create_all), shutdown runs on exit (dispose)
