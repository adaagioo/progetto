import pytest
import httpx
from backend.main import app


@pytest.mark.anyio
async def test_login_unauthorized(monkeypatch):
	from backend.app.repositories import users_repo

	async def fake_find_by_email(email: str):
		return None

	monkeypatch.setattr(users_repo, "find_by_email", fake_find_by_email)

	transport = httpx.ASGITransport(app=app)
	async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
		r = await ac.post(
			"/api/v1/auth/login",
			json={"email": "x@y.z", "password": "pw"},
		)

	assert r.status_code in (400, 401)
