import pytest
from fastapi import HTTPException

import server.routers.auth as auth_routes
from tests.backend.conftest import TestUser, TestAnalysis


def test_invalid_credentials_exception():
    exc = auth_routes.invalid_credentials_exception()

    assert isinstance(exc, HTTPException)
    assert exc.status_code == 401
    assert exc.detail == "Invalid credentials"
    assert exc.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_authenticate_user_normalizes_username(test_user):
    user = await auth_routes.authenticate_user(" TESTUSER ", "Secret123!")

    assert user == test_user


@pytest.mark.asyncio
async def test_authenticate_user_returns_none_when_user_missing():
    user = await auth_routes.authenticate_user("missing", "Secret123!")

    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_returns_none_when_password_invalid(test_user):
    user = await auth_routes.authenticate_user("testuser", "bad-password")

    assert user is None


@pytest.mark.asyncio
async def test_safe_delete_file_ignores_empty_file_id(monkeypatch):
    called = {"delete": False}

    async def test_delete_file(file_id):
        called["delete"] = True

    monkeypatch.setattr(auth_routes, "delete_file", test_delete_file)

    await auth_routes.safe_delete_file(None)
    await auth_routes.safe_delete_file("")
    await auth_routes.safe_delete_file(0)

    assert called["delete"] is False


@pytest.mark.asyncio
async def test_safe_delete_file_deletes_file(monkeypatch):
    deleted_files = []

    async def test_delete_file(file_id):
        deleted_files.append(file_id)

    monkeypatch.setattr(auth_routes, "delete_file", test_delete_file)

    await auth_routes.safe_delete_file("file-id")

    assert deleted_files == ["file-id"]


@pytest.mark.asyncio
async def test_safe_delete_file_ignores_delete_errors(monkeypatch):
    async def failing_delete_file(file_id):
        raise RuntimeError("delete failed")

    monkeypatch.setattr(auth_routes, "delete_file", failing_delete_file)

    await auth_routes.safe_delete_file("file-id")


@pytest.mark.asyncio
async def test_delete_nested_files_deletes_plain_value(monkeypatch):
    deleted_files = []

    async def test_delete_file(file_id):
        deleted_files.append(file_id)

    monkeypatch.setattr(auth_routes, "delete_file", test_delete_file)

    await auth_routes.delete_nested_files("file-a")

    assert deleted_files == ["file-a"]


@pytest.mark.asyncio
async def test_delete_nested_files_deletes_nested_values(monkeypatch):
    deleted_files = []

    async def test_delete_file(file_id):
        deleted_files.append(file_id)

    monkeypatch.setattr(auth_routes, "delete_file", test_delete_file)

    await auth_routes.delete_nested_files(
        {
            "a": "file-a",
            "b": ["file-b", {"c": "file-c"}],
            "d": None,
            "e": "",
        }
    )

    assert deleted_files == ["file-a", "file-b", "file-c"]


@pytest.mark.asyncio
async def test_delete_analysis_files_deletes_all_known_files(monkeypatch, authenticated_test_user):
    deleted_files = []

    async def test_delete_file(file_id):
        deleted_files.append(file_id)

    monkeypatch.setattr(auth_routes, "delete_file", test_delete_file)

    analysis = TestAnalysis(user_id=authenticated_test_user.id)
    analysis.raw_dataset_file_id = "raw-file"
    analysis.normalized_dataset_file_id = "normalized-file"
    analysis.metrics_config_file_id = "metrics-file"
    analysis.filtered_dataset_file_ids = {
        "a": "filtered-file-a",
        "b": "filtered-file-b",
    }
    analysis.outputs = {
        "plot": "plot-file",
        "nested": {
            "items": ["nested-file-1", "nested-file-2"],
        },
    }

    await auth_routes.delete_analysis_files(analysis)

    assert deleted_files == [
        "raw-file",
        "normalized-file",
        "metrics-file",
        "filtered-file-a",
        "filtered-file-b",
        "plot-file",
        "nested-file-1",
        "nested-file-2",
    ]


def test_register_success(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "TestUser",
            "email": "TESTUSER@example.com",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 201, response.json()

    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"
    assert "id" in data
    assert "created_at" in data

    assert len(TestUser.users) == 1
    assert TestUser.users[0].password_hash == "hashed:Secret123!"


def test_register_fails_when_username_exists(client, test_user):
    response = client.post(
        "/auth/register",
        json={
            "username": "TESTUSER",
            "email": "other@example.com",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 400, response.json()
    assert response.json()["detail"] == "Username already exists"


def test_register_fails_when_email_exists(client, test_user):
    response = client.post(
        "/auth/register",
        json={
            "username": "other",
            "email": "TESTUSER@example.com",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 400, response.json()
    assert response.json()["detail"] == "Email already exists"


def test_login_success(client, test_user):
    response = client.post(
        "/auth/login",
        json={
            "username": " TESTUSER ",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 200, response.json()
    assert response.json() == {
        "access_token": f"token-for-{test_user.id}",
        "token_type": "bearer",
    }


def test_login_fails_with_wrong_password(client, test_user):
    response = client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "WrongSecret123!",
        },
    )

    assert response.status_code == 401, response.json()
    assert response.json()["detail"] == "Invalid credentials"
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_fails_with_unknown_user(client):
    response = client.post(
        "/auth/login",
        json={
            "username": "missing",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 401, response.json()
    assert response.json()["detail"] == "Invalid credentials"


def test_token_login_success(client, test_user):
    response = client.post(
        "/auth/token",
        data={
            "username": "testuser",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 200, response.json()
    assert response.json() == {
        "access_token": f"token-for-{test_user.id}",
        "token_type": "bearer",
    }


def test_token_login_fails_with_wrong_password(client, test_user):
    response = client.post(
        "/auth/token",
        data={
            "username": "testuser",
            "password": "WrongSecret123!",
        },
    )

    assert response.status_code == 401, response.json()
    assert response.json()["detail"] == "Invalid credentials"


def test_me_success(client, authenticated_test_user):
    response = client.get("/auth/me")

    assert response.status_code == 200, response.json()

    data = response.json()
    assert data["id"] == str(authenticated_test_user.id)
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"
    assert "created_at" in data


def test_update_user_success(client, authenticated_test_user):
    response = client.patch(
        "/auth/me",
        json={
            "username": "UpdatedTestUser",
            "email": "updated@example.com",
        },
    )

    assert response.status_code == 200, response.json()
    assert response.json() == {"message": "User updated"}

    assert authenticated_test_user.username == "updatedtestuser"
    assert authenticated_test_user.email == "updated@example.com"
    assert authenticated_test_user.saved is True


def test_update_user_only_username(client, authenticated_test_user):
    response = client.patch(
        "/auth/me",
        json={
            "username": "OnlyUsername",
        },
    )

    assert response.status_code == 200, response.json()
    assert response.json() == {"message": "User updated"}
    assert authenticated_test_user.username == "onlyusername"
    assert authenticated_test_user.email == "testuser@example.com"
    assert authenticated_test_user.saved is True


def test_update_user_only_email(client, authenticated_test_user):
    response = client.patch(
        "/auth/me",
        json={
            "email": "ONLYEMAIL@example.com",
        },
    )

    assert response.status_code == 200, response.json()
    assert response.json() == {"message": "User updated"}
    assert authenticated_test_user.username == "testuser"
    assert authenticated_test_user.email == "onlyemail@example.com"
    assert authenticated_test_user.saved is True


def test_update_user_with_empty_payload_still_saves(client, authenticated_test_user):
    response = client.patch("/auth/me", json={})

    assert response.status_code == 200, response.json()
    assert response.json() == {"message": "User updated"}
    assert authenticated_test_user.username == "testuser"
    assert authenticated_test_user.email == "testuser@example.com"
    assert authenticated_test_user.saved is True


def test_update_user_fails_when_username_exists(client, authenticated_test_user):
    existing_user = TestUser(
        username="taken",
        email="taken@example.com",
        password_hash="hashed:Secret123!",
    )
    TestUser.users.append(existing_user)

    response = client.patch(
        "/auth/me",
        json={
            "username": "TAKEN",
        },
    )

    assert response.status_code == 400, response.json()
    assert response.json()["detail"] == "Username already exists"


def test_update_user_fails_when_email_exists(client, authenticated_test_user):
    existing_user = TestUser(
        username="other",
        email="taken@example.com",
        password_hash="hashed:Secret123!",
    )
    TestUser.users.append(existing_user)

    response = client.patch(
        "/auth/me",
        json={
            "email": "TAKEN@example.com",
        },
    )

    assert response.status_code == 400, response.json()
    assert response.json()["detail"] == "Email already exists"


def test_change_password_success(client, authenticated_test_user):
    response = client.patch(
        "/auth/password",
        json={
            "current_password": "Secret123!",
            "new_password": "NewSecret123!",
        },
    )

    assert response.status_code == 200, response.json()
    assert response.json() == {"message": "Password updated"}

    assert authenticated_test_user.password_hash == "hashed:NewSecret123!"
    assert authenticated_test_user.saved is True


def test_change_password_fails_with_wrong_current_password(
    client,
    authenticated_test_user,
):
    response = client.patch(
        "/auth/password",
        json={
            "current_password": "WrongSecret123!",
            "new_password": "NewSecret123!",
        },
    )

    assert response.status_code == 401, response.json()
    assert response.json()["detail"] == "Current password incorrect"
    assert response.headers["www-authenticate"] == "Bearer"


def test_delete_account_success(client, authenticated_test_user, monkeypatch):
    deleted_files = []

    async def test_delete_file(file_id):
        deleted_files.append(file_id)

    monkeypatch.setattr(auth_routes, "delete_file", test_delete_file)

    analysis = TestAnalysis(user_id=authenticated_test_user.id)
    analysis.raw_dataset_file_id = "raw-file"
    analysis.normalized_dataset_file_id = "normalized-file"
    analysis.metrics_config_file_id = "metrics-file"
    analysis.filtered_dataset_file_ids = {
        "a": "filtered-file-a",
        "b": "filtered-file-b",
    }
    analysis.outputs = {
        "plot": "plot-file",
        "nested": {
            "items": ["nested-file-1", "nested-file-2"],
        },
    }

    TestAnalysis.analyses.append(analysis)

    response = client.delete("/auth/me")

    assert response.status_code == 200, response.json()
    assert response.json() == {"message": "Account deleted"}

    assert authenticated_test_user.deleted is True
    assert analysis.deleted is True

    assert deleted_files == [
        "raw-file",
        "normalized-file",
        "metrics-file",
        "filtered-file-a",
        "filtered-file-b",
        "plot-file",
        "nested-file-1",
        "nested-file-2",
    ]


def test_delete_account_deletes_only_authenticated_user_analyses(
    client,
    authenticated_test_user,
    monkeypatch,
):
    deleted_files = []

    async def test_delete_file(file_id):
        deleted_files.append(file_id)

    monkeypatch.setattr(auth_routes, "delete_file", test_delete_file)

    own_analysis = TestAnalysis(user_id=authenticated_test_user.id)
    own_analysis.raw_dataset_file_id = "own-raw-file"

    other_user = TestUser(
        username="other",
        email="other@example.com",
        password_hash="hashed:Secret123!",
    )
    other_analysis = TestAnalysis(user_id=other_user.id)
    other_analysis.raw_dataset_file_id = "other-raw-file"

    TestAnalysis.analyses.extend([own_analysis, other_analysis])

    response = client.delete("/auth/me")

    assert response.status_code == 200, response.json()
    assert own_analysis.deleted is True
    assert other_analysis.deleted is False
    assert deleted_files == ["own-raw-file"]


def test_delete_account_continues_if_file_delete_fails(
    client,
    authenticated_test_user,
    monkeypatch,
):
    async def failing_delete_file(file_id):
        raise RuntimeError("gridfs failed")

    monkeypatch.setattr(auth_routes, "delete_file", failing_delete_file)

    analysis = TestAnalysis(user_id=authenticated_test_user.id)
    analysis.raw_dataset_file_id = "raw-file"
    analysis.outputs = {"plot": "plot-file"}
    TestAnalysis.analyses.append(analysis)

    response = client.delete("/auth/me")

    assert response.status_code == 200, response.json()
    assert response.json() == {"message": "Account deleted"}
    assert analysis.deleted is True
    assert authenticated_test_user.deleted is True


def test_delete_account_returns_500_if_analysis_delete_fails(
    client,
    authenticated_test_user,
    monkeypatch,
):
    async def failing_analysis_delete(self):
        raise RuntimeError("analysis delete error")

    analysis = TestAnalysis(user_id=authenticated_test_user.id)
    TestAnalysis.analyses.append(analysis)

    monkeypatch.setattr(TestAnalysis, "delete", failing_analysis_delete)

    response = client.delete("/auth/me")

    assert response.status_code == 500, response.json()
    assert response.json()["detail"] == (
        "Failed to delete account: analysis delete error"
    )


def test_delete_account_returns_500_if_user_delete_fails(
    client,
    authenticated_test_user,
    monkeypatch,
):
    async def failing_delete(self):
        raise RuntimeError("database error")

    monkeypatch.setattr(TestUser, "delete", failing_delete)

    response = client.delete("/auth/me")

    assert response.status_code == 500, response.json()
    assert response.json()["detail"] == "Failed to delete account: database error"
