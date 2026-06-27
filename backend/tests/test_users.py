import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.department import Department

@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    """Verify unauthorized requests to protected endpoints return 401."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"

@pytest.mark.asyncio
async def test_get_me_authorized(client: AsyncClient):
    """Verify authorized requests return user profile details."""
    # 1. Login to get access token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Query /users/me
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["full_name"] == "Test Admin"
    assert data["role_id"] == "ADMIN"
    assert "department" in data

@pytest.mark.asyncio
async def test_admin_create_user(client: AsyncClient, db: AsyncSession):
    """Verify users:write permissions allow creating a new user profile."""
    # 1. Login as Admin
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get department ID to assign
    result = await db.execute(select(Department).where(Department.code == "ENG"))
    dept = result.scalar_one()

    # 3. Create user request
    new_user_data = {
        "email": "engineer@test.com",
        "full_name": "Test Engineer",
        "password": "EngineerPass123!",
        "role_id": "ENGINEER",
        "department_id": str(dept.id)
    }

    response = await client.post("/api/v1/users", json=new_user_data, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "engineer@test.com"
    assert data["role_id"] == "ENGINEER"

@pytest.mark.asyncio
async def test_rbac_restriction(client: AsyncClient, db: AsyncSession):
    """Verify non-admin roles cannot create users."""
    # 1. Setup engineer user in DB
    result = await db.execute(select(Department).where(Department.code == "ENG"))
    dept = result.scalar_one()
    
    from app.core.security import hash_password
    engineer_user = User(
        email="eng@test.com",
        hashed_password=hash_password("EngPass123!"),
        full_name="Eng Test",
        role_id="ENGINEER",
        department_id=dept.id
    )
    db.add(engineer_user)
    await db.commit()

    # 2. Login as Engineer
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "eng@test.com", "password": "EngPass123!"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Try to call user create
    response = await client.post(
        "/api/v1/users",
        json={
            "email": "other@test.com",
            "full_name": "Other User",
            "password": "Password123!",
            "role_id": "VIEWER"
        },
        headers=headers
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "AUTHORIZATION_FAILED"

@pytest.mark.asyncio
async def test_list_departments(client: AsyncClient):
    """Verify that any authenticated user can retrieve the corporate departments list."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/users/departments", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(d["code"] == "ENG" for d in data)
