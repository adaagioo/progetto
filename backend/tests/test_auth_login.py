import pytest
from httpx import AsyncClient
from app.main import create_app


@pytest.mark.asyncio
async def test_login_unauthorized(monkeypatch):
	async def fake_find_by_email(email: str):
		return None  # nessun utente -> 401

	from app.repositories import users_repo
	monkeypatch.setattr(users_repo, "find_by_email", fake_find_by_email)

	app = create_app()
	async with AsyncClient(app=app, base_url="http://test") as ac:
		resp = await ac.post("/api/v1/auth/login", json={"email": "x@y.z", "password": "pw"})
	assert resp.status_code == 401
