import pytest
import httpx
from backend.main import app


@pytest.mark.anyio
async def test_health_live():
	transport = httpx.ASGITransport(app=app)
	async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
		r = await ac.get("/api/v1/health/live")
	assert r.status_code == 200
	assert r.json().get("status") in {"ok", "live", "ready", "healthy"}


@pytest.mark.Anyio
async def test_health_ready():
	transport = httpx.ASGITransport(app=app)
	async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
		r = await ac.get("/api/v1/health/ready")
	assert r.status_code == 200
	assert r.json().get("status") in {"ok", "ready", "healthy"}
