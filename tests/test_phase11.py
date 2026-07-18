"""Tests for Phase 11 features: enhanced Excel/PDF export, auto-close tasks, cleanup."""
from __future__ import annotations

import time
import warnings
from datetime import date, timedelta

import pytest

warnings.filterwarnings("ignore")


@pytest.fixture()
def client():
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    from api.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


def _register_and_login(client, email="admin@test.com", tenant="Co"):
    client.post("/api/auth/register", json={
        "email": email, "password": "pass123", "name": "Admin", "tenant_name": tenant,
    })
    r = client.post("/api/auth/login", data={"username": email, "password": "pass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _setup_and_generate(client, h, num_days=7):
    pids = []
    for name in ["Day", "Night"]:
        r = client.post("/api/patterns", headers=h, json={
            "name": name, "type": "work",
            "start_time": "09:00", "end_time": "17:00",
            "work_hours": 7.0, "break_hours": 1.0,
        })
        pids.append(r.json()["id"])

    mids = []
    for name in ["Alice", "Bob", "Charlie"]:
        r = client.post("/api/members", headers=h, json={
            "name": name, "available_pattern_ids": pids,
        })
        mids.append(r.json()["id"])

    r = client.post("/api/schedules", headers=h, json={
        "name": "TestSchedule", "start_date": "2026-07-01", "num_days": num_days,
    })
    sid = r.json()["id"]

    client.post(f"/api/schedules/{sid}/demands/batch", headers=h,
                json={"min_total": 1, "max_total": 3})

    client.post(f"/api/schedules/{sid}/pattern-demands/batch", headers=h,
                json={"pattern_id": pids[0], "min_count": 1})

    r = client.post("/api/groups", headers=h, json={
        "name": "TeamA", "member_ids": mids[:2],
    })
    gid = r.json()["id"]
    client.post(f"/api/schedules/{sid}/group-demands/batch", headers=h,
                json={"group_id": gid, "min_count": 1})

    r = client.post(f"/api/schedules/{sid}/generate", headers=h)
    assert r.status_code == 200

    time.sleep(15)

    r = client.get(f"/api/schedules/{sid}", headers=h)
    assert r.json()["status"] == "completed"

    return sid, pids, mids, gid


class TestExcelExport:
    def test_excel_export_returns_xlsx(self, client):
        h = _register_and_login(client)
        sid, *_ = _setup_and_generate(client, h)

        r = client.get(f"/api/schedules/{sid}/export/excel", headers=h)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers["content-type"]
        assert len(r.content) > 1000

    def test_excel_export_not_completed_returns_400(self, client):
        h = _register_and_login(client)
        r = client.post("/api/schedules", headers=h, json={
            "name": "Draft", "start_date": "2026-07-01", "num_days": 7,
        })
        sid = r.json()["id"]
        r = client.get(f"/api/schedules/{sid}/export/excel", headers=h)
        assert r.status_code == 400


class TestPdfExport:
    def test_pdf_export_returns_pdf(self, client):
        h = _register_and_login(client)
        sid, *_ = _setup_and_generate(client, h)

        r = client.get(f"/api/schedules/{sid}/export/pdf", headers=h)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"

    def test_pdf_export_not_completed_returns_400(self, client):
        h = _register_and_login(client)
        r = client.post("/api/schedules", headers=h, json={
            "name": "Draft", "start_date": "2026-07-01", "num_days": 7,
        })
        sid = r.json()["id"]
        r = client.get(f"/api/schedules/{sid}/export/pdf", headers=h)
        assert r.status_code == 400


class TestPatternDemands:
    def test_batch_and_list(self, client):
        h = _register_and_login(client)
        r = client.post("/api/patterns", headers=h, json={
            "name": "Morning", "type": "work",
            "start_time": "08:00", "end_time": "16:00", "work_hours": 7.0,
        })
        pid = r.json()["id"]

        r = client.post("/api/schedules", headers=h, json={
            "name": "S", "start_date": "2026-07-01", "num_days": 7,
        })
        sid = r.json()["id"]

        r = client.post(f"/api/schedules/{sid}/pattern-demands/batch", headers=h,
                        json={"pattern_id": pid, "min_count": 2})
        assert r.status_code == 200
        assert len(r.json()) == 7

        r = client.get(f"/api/schedules/{sid}/pattern-demands", headers=h)
        assert len(r.json()) == 7
        assert all(pd["min_count"] == 2 for pd in r.json())

    def test_update_pattern_demand(self, client):
        h = _register_and_login(client)
        r = client.post("/api/patterns", headers=h, json={
            "name": "Morning", "type": "work",
            "start_time": "08:00", "end_time": "16:00", "work_hours": 7.0,
        })
        pid = r.json()["id"]

        r = client.post("/api/schedules", headers=h, json={
            "name": "S", "start_date": "2026-07-01", "num_days": 7,
        })
        sid = r.json()["id"]

        client.post(f"/api/schedules/{sid}/pattern-demands/batch", headers=h,
                    json={"pattern_id": pid, "min_count": 1})
        r = client.get(f"/api/schedules/{sid}/pattern-demands", headers=h)
        pdid = r.json()[0]["id"]

        r = client.put(f"/api/schedules/{sid}/pattern-demands/{pdid}", headers=h,
                       json={"min_count": 5})
        assert r.status_code == 200

        r = client.get(f"/api/schedules/{sid}/pattern-demands", headers=h)
        updated = [pd for pd in r.json() if pd["id"] == pdid]
        assert updated[0]["min_count"] == 5

    def test_clear(self, client):
        h = _register_and_login(client)
        r = client.post("/api/patterns", headers=h, json={
            "name": "Morning", "type": "work",
            "start_time": "08:00", "end_time": "16:00", "work_hours": 7.0,
        })
        pid = r.json()["id"]

        r = client.post("/api/schedules", headers=h, json={
            "name": "S", "start_date": "2026-07-01", "num_days": 7,
        })
        sid = r.json()["id"]

        client.post(f"/api/schedules/{sid}/pattern-demands/batch", headers=h,
                    json={"pattern_id": pid, "min_count": 2})
        r = client.delete(f"/api/schedules/{sid}/pattern-demands", headers=h)
        assert r.status_code == 204

        r = client.get(f"/api/schedules/{sid}/pattern-demands", headers=h)
        assert len(r.json()) == 0


class TestGroupDemandsBatch:
    def test_batch_and_update(self, client):
        h = _register_and_login(client)
        pids = []
        for name in ["Day"]:
            r = client.post("/api/patterns", headers=h, json={
                "name": name, "type": "work",
                "start_time": "09:00", "end_time": "17:00", "work_hours": 7.0,
            })
            pids.append(r.json()["id"])

        mids = []
        for name in ["A", "B"]:
            r = client.post("/api/members", headers=h, json={
                "name": name, "available_pattern_ids": pids,
            })
            mids.append(r.json()["id"])

        r = client.post("/api/groups", headers=h, json={
            "name": "G1", "member_ids": mids,
        })
        gid = r.json()["id"]

        r = client.post("/api/schedules", headers=h, json={
            "name": "S", "start_date": "2026-07-01", "num_days": 7,
        })
        sid = r.json()["id"]

        r = client.post(f"/api/schedules/{sid}/group-demands/batch", headers=h,
                        json={"group_id": gid, "min_count": 1})
        assert r.status_code == 200
        assert len(r.json()) == 7

        r = client.get(f"/api/schedules/{sid}/group-demands", headers=h)
        gdid = r.json()[0]["id"]

        r = client.put(f"/api/schedules/{sid}/group-demands/{gdid}", headers=h,
                       json={"min_count": 2})
        assert r.status_code == 200


class TestScheduleUpdate:
    def test_update_schedule_name(self, client):
        h = _register_and_login(client)
        r = client.post("/api/schedules", headers=h, json={
            "name": "Original", "start_date": "2026-07-01", "num_days": 7,
        })
        sid = r.json()["id"]

        r = client.put(f"/api/schedules/{sid}", headers=h, json={"name": "Updated"})
        assert r.status_code == 200
        assert r.json()["name"] == "Updated"


class TestAutoCloseTasks:
    def test_auto_close_endpoint(self, client):
        h = _register_and_login(client)
        r = client.post("/api/tasks/auto-close-rest-requests")
        assert r.status_code == 200
        assert r.json()["closed_schedules"] == 0

    def test_cleanup_endpoint(self, client):
        h = _register_and_login(client)
        r = client.post("/api/tasks/cleanup-old-data")
        assert r.status_code == 200
        assert r.json()["cleaned_schedules"] == 0

    def test_auto_close_with_expired_deadline(self, client):
        h = _register_and_login(client)
        pids = []
        for name in ["Day"]:
            r = client.post("/api/patterns", headers=h, json={
                "name": name, "type": "work",
                "start_time": "09:00", "end_time": "17:00", "work_hours": 7.0,
            })
            pids.append(r.json()["id"])

        mids = []
        for name in ["M1", "M2"]:
            r = client.post("/api/members", headers=h, json={
                "name": name, "available_pattern_ids": pids,
            })
            mids.append(r.json()["id"])

        yesterday = str(date.today() - timedelta(days=1))
        r = client.post("/api/schedules", headers=h, json={
            "name": "Expired", "start_date": "2026-07-01", "num_days": 7,
            "rest_request_deadline": yesterday,
        })
        sid = r.json()["id"]

        client.post(f"/api/schedules/{sid}/rest-requests/open", headers=h)

        r = client.get(f"/api/members/{mids[0]}/token", headers=h)
        token = r.json()["personal_token"]
        client.put(f"/api/personal/schedules/{sid}/rest-request",
                   params={"token": token},
                   json={"requested_dates": ["2026-07-03"]})

        r = client.post("/api/tasks/auto-close-rest-requests")
        assert r.status_code == 200
        data = r.json()
        assert data["closed_schedules"] == 1
        assert data["auto_submitted"] == 2
        assert data["fixed_assignments_created"] == 1

        r = client.get(f"/api/schedules/{sid}/fixed-assignments", headers=h)
        assert len(r.json()) == 1
        assert r.json()[0]["type"] == "rest"
