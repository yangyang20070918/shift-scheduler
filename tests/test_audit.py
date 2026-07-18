"""Tests for audit logging feature."""
from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")


def _client():
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    from api.main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


def _register_and_login(client, email="admin@test.com", tenant="Co"):
    client.post("/api/auth/register", json={
        "email": email, "password": "pass123", "name": "Admin", "tenant_name": tenant,
    })
    r = client.post("/api/auth/login", data={"username": email, "password": "pass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestAuditLog:
    def test_login_creates_audit_log(self):
        with _client() as c:
            h = _register_and_login(c)
            r = c.get("/api/audit-logs", headers=h)
            assert r.status_code == 200
            data = r.json()
            assert data["total"] >= 2
            actions = [item["action"] for item in data["items"]]
            assert "LOGIN" in actions
            assert "REGISTER" in actions

    def test_crud_creates_audit_logs(self):
        with _client() as c:
            h = _register_and_login(c)

            c.post("/api/patterns", headers=h, json={
                "name": "Day", "type": "work",
                "start_time": "09:00", "end_time": "17:00", "work_hours": 7.0,
            })

            c.post("/api/members", headers=h, json={
                "name": "TestMember", "available_pattern_ids": [],
            })

            r = c.get("/api/audit-logs", headers=h)
            data = r.json()
            actions = [item["action"] for item in data["items"]]
            assert "CREATE" in actions
            resources = [item["resource_type"] for item in data["items"]]
            assert "pattern" in resources
            assert "member" in resources

    def test_audit_log_filter_by_action(self):
        with _client() as c:
            h = _register_and_login(c)

            c.post("/api/members", headers=h, json={
                "name": "A", "available_pattern_ids": [],
            })

            r = c.get("/api/audit-logs", headers=h, params={"action": "CREATE"})
            data = r.json()
            assert all(item["action"] == "CREATE" for item in data["items"])

    def test_audit_log_filter_by_resource(self):
        with _client() as c:
            h = _register_and_login(c)

            c.post("/api/members", headers=h, json={
                "name": "B", "available_pattern_ids": [],
            })

            r = c.get("/api/audit-logs", headers=h, params={"resource_type": "member"})
            data = r.json()
            assert all(item["resource_type"] == "member" for item in data["items"])

    def test_audit_stats(self):
        with _client() as c:
            h = _register_and_login(c)

            c.post("/api/members", headers=h, json={
                "name": "C", "available_pattern_ids": [],
            })

            r = c.get("/api/audit-logs/stats", headers=h)
            assert r.status_code == 200
            data = r.json()
            assert data["total"] >= 3
            assert len(data["by_action"]) > 0
            assert len(data["by_resource"]) > 0

    def test_update_and_delete_logged(self):
        with _client() as c:
            h = _register_and_login(c)

            r = c.post("/api/members", headers=h, json={
                "name": "Original", "available_pattern_ids": [],
            })
            mid = r.json()["id"]

            c.put(f"/api/members/{mid}", headers=h, json={
                "name": "Updated", "available_pattern_ids": [],
            })

            c.delete(f"/api/members/{mid}", headers=h)

            r = c.get("/api/audit-logs", headers=h, params={"resource_type": "member"})
            actions = [item["action"] for item in r.json()["items"]]
            assert "CREATE" in actions
            assert "UPDATE" in actions
            assert "DELETE" in actions

    def test_schedule_generate_logged(self):
        with _client() as c:
            h = _register_and_login(c)

            r = c.post("/api/schedules", headers=h, json={
                "name": "TestSch", "start_date": "2026-08-01", "num_days": 7,
            })
            sid = r.json()["id"]

            r = c.get("/api/audit-logs", headers=h, params={"resource_type": "schedule"})
            actions = [item["action"] for item in r.json()["items"]]
            assert "CREATE" in actions
