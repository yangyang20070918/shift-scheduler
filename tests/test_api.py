"""API integration tests for the shift scheduler web layer."""
from __future__ import annotations

import time
import warnings

import pytest

warnings.filterwarnings("ignore")


@pytest.fixture()
def client():
    import os
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from api.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    client.post("/api/auth/register", json={
        "email": "test@example.com", "password": "pass123",
        "name": "Tester", "tenant_name": "TestCo",
    })
    r = client.post("/api/auth/login", data={"username": "test@example.com", "password": "pass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestAuth:
    def test_register(self, client):
        r = client.post("/api/auth/register", json={
            "email": "new@test.com", "password": "abc123",
            "name": "New", "tenant_name": "Co",
        })
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_register_duplicate_email(self, client):
        client.post("/api/auth/register", json={
            "email": "dup@test.com", "password": "xxxxxx",
            "name": "A", "tenant_name": "B",
        })
        r = client.post("/api/auth/register", json={
            "email": "dup@test.com", "password": "yyyyyy",
            "name": "C", "tenant_name": "D",
        })
        assert r.status_code == 409

    def test_login_success(self, client):
        client.post("/api/auth/register", json={
            "email": "login@test.com", "password": "secret",
            "name": "L", "tenant_name": "T",
        })
        r = client.post("/api/auth/login", data={"username": "login@test.com", "password": "secret"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={
            "email": "wp@test.com", "password": "right",
            "name": "W", "tenant_name": "T",
        })
        r = client.post("/api/auth/login", data={"username": "wp@test.com", "password": "wrong"})
        assert r.status_code == 401

    def test_me(self, client, auth_headers):
        r = client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["email"] == "test@example.com"

    def test_unauthorized(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401


class TestPatterns:
    def test_create_and_list(self, client, auth_headers):
        r = client.post("/api/patterns", headers=auth_headers, json={
            "name": "Morning", "type": "work",
            "start_time": "08:00", "end_time": "16:00",
            "work_hours": 7.0, "break_hours": 1.0,
        })
        assert r.status_code == 201
        pid = r.json()["id"]

        r = client.get("/api/patterns", headers=auth_headers)
        assert r.status_code == 200
        assert any(p["id"] == pid for p in r.json())

    def test_delete_pattern(self, client, auth_headers):
        r = client.post("/api/patterns", headers=auth_headers, json={
            "name": "Temp", "type": "work",
            "start_time": "09:00", "end_time": "17:00",
            "work_hours": 7.0,
        })
        pid = r.json()["id"]

        r = client.delete(f"/api/patterns/{pid}", headers=auth_headers)
        assert r.status_code == 204


class TestMembers:
    def test_crud(self, client, auth_headers):
        r = client.post("/api/members", headers=auth_headers, json={
            "name": "Alice", "available_pattern_ids": [],
        })
        assert r.status_code == 201
        mid = r.json()["id"]

        r = client.put(f"/api/members/{mid}", headers=auth_headers, json={
            "name": "Alice W", "available_pattern_ids": [],
        })
        assert r.status_code == 200
        assert r.json()["name"] == "Alice W"

        r = client.delete(f"/api/members/{mid}", headers=auth_headers)
        assert r.status_code == 204

    def test_list(self, client, auth_headers):
        client.post("/api/members", headers=auth_headers, json={"name": "Bob"})
        r = client.get("/api/members", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1


class TestSchedules:
    def test_create_and_list(self, client, auth_headers):
        r = client.post("/api/schedules", headers=auth_headers, json={
            "name": "July", "start_date": "2026-07-01", "num_days": 31,
        })
        assert r.status_code == 201
        assert r.json()["status"] == "draft"

        r = client.get("/api/schedules", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_generate(self, client, auth_headers):
        # Setup patterns and members
        pids = []
        for name in ["Day", "Night"]:
            r = client.post("/api/patterns", headers=auth_headers, json={
                "name": name, "type": "work",
                "start_time": "09:00", "end_time": "17:00",
                "work_hours": 7.0, "break_hours": 1.0,
            })
            pids.append(r.json()["id"])

        for name in ["A", "B", "C"]:
            client.post("/api/members", headers=auth_headers, json={
                "name": name, "available_pattern_ids": pids,
            })

        # Create and generate
        r = client.post("/api/schedules", headers=auth_headers, json={
            "name": "Test", "start_date": "2026-07-01", "num_days": 7,
        })
        sid = r.json()["id"]

        r = client.post(f"/api/schedules/{sid}/generate", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "running"

        # Wait for background task
        time.sleep(15)

        r = client.get(f"/api/schedules/{sid}", headers=auth_headers)
        result = r.json()
        assert result["status"] == "completed"
        assert len(result["assignments"]) == 21  # 3 members * 7 days


class TestTenantIsolation:
    def test_tenant_data_isolation(self, client):
        # Register two users in different tenants
        client.post("/api/auth/register", json={
            "email": "user1@a.com", "password": "passw1", "name": "U1", "tenant_name": "TenantA",
        })
        r = client.post("/api/auth/login", data={"username": "user1@a.com", "password": "passw1"})
        h1 = {"Authorization": f"Bearer {r.json()['access_token']}"}

        client.post("/api/auth/register", json={
            "email": "user2@b.com", "password": "passw1", "name": "U2", "tenant_name": "TenantB",
        })
        r = client.post("/api/auth/login", data={"username": "user2@b.com", "password": "passw1"})
        h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # Tenant A creates a member
        client.post("/api/members", headers=h1, json={"name": "OnlyA"})

        # Tenant B should not see it
        r = client.get("/api/members", headers=h2)
        assert all(m["name"] != "OnlyA" for m in r.json())
