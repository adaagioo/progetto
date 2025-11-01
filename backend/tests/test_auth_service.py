import pytest
from app.services import auth_service


def test_create_access_token_roundtrip():
	token = auth_service.create_access_token("user-id")
	assert isinstance(token, str)
