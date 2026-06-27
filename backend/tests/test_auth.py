import pytest
from httpx import AsyncClient
from app.core.security import hash_password, verify_password

def test_password_utilities():
    """Verify password crypting and validation functions work correctly."""
    pwd = "MySuperSecretPassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Verify correct credentials return access and refresh tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_failure(client: AsyncClient):
    """Verify incorrect credentials return 401 Authentication error envelope."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "WrongPassword!"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"

@pytest.mark.asyncio
async def test_refresh_token_cycle(client: AsyncClient):
    """Verify refresh token can successfully fetch new access token."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
