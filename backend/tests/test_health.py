import pytest
from httpx import AsyncClient
from backend.app.main import create_app


@pytest.mark.asyncio
async def test_healthz():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
