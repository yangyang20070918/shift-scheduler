"""Comprehensive API integration tests — CRUD, rest-request lifecycle,
personal-token auth, and multi-tenant data isolation."""
from __future__ import annotations

import time
import warnings

import pytest

warnings.filterwarnings("ignore")


# ── fixtures ──────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    from api.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


def _register_and_login(client, email, password="pass123", name="User", tenant="Co"):
    client.post("/api/auth/register", json={
        "email": email, "password": password,
        "name": name, "tenant_name": tenant,
    })
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def h(client):
    return _register_and_login(client, "admin@test.com", tenant="TestCo")


def _create_patterns(client, h, names=("Day", "Night")):
    pids = []
    for n in names:
        r = client.post("/api/patterns", headers=h, json={
            "name": n, "type": "work",
            "start_time": "09:00", "end_time": "17:00",
            "work_hours": 7.0, "break_hours": 1.0,
        })
        pids.append(r.json()["id"])
    return pids


def _create_members(client, h, pids, names=("A", "B", "C")):
    mids = []
    for n in names:
        r = client.post("/api/members", headers=h, json={
            "name": n, "available_pattern_ids": pids,
        })
        mids.append(r.json()["id"])
    return mids


def _create_schedule(client, h, name="Sched", start="2026-07-01", days=7, **kwargs):
    r = client.post("/api/schedules", headers=h, json={
        "name": name, "start_date": start, "num_days": days, **kwargs,
    })
    assert r.status_code == 201
    return r.json()["id"]


# ── Demands CRUD ──────────────────────────────────────────────────────

class TestDemands:
    def test_batch_and_list(self, client, h):
        sid = _create_schedule(client, h)
        r = client.post(f"/api/schedules/{sid}/demands/batch", headers=h,
                        json={"min_total": 2, "max_total": 5})
        assert r.status_code == 200
        assert len(r.json()) == 7

        r = client.get(f"/api/schedules/{sid}/demands", headers=h)
        assert len(r.json()) == 7

    def test_create_single(self, client, h):
        sid = _create_schedule(client, h)
        r = client.post(f"/api/schedules/{sid}/demands", headers=h,
                        json={"date": "2026-07-01", "min_total": 1, "max_total": 3})
        assert r.status_code == 201

    def test_clear(self, client, h):
        sid = _create_schedule(client, h)
        client.post(f"/api/schedules/{sid}/demands/batch", headers=h,
                    json={"min_total": 2, "max_total": 5})
        r = client.delete(f"/api/schedules/{sid}/demands", headers=h)
        assert r.status_code == 204
        r = client.get(f"/api/schedules/{sid}/demands", headers=h)
        assert len(r.json()) == 0

    def test_other_tenant_cannot_access(self, client, h):
        sid = _create_schedule(client, h)
        h2 = _register_and_login(client, "other@test.com", tenant="OtherCo")
        r = client.get(f"/api/schedules/{sid}/demands", headers=h2)
        assert r.status_code == 404


# ── Fixed Assignments CRUD ────────────────────────────────────────────

class TestFixedAssignments:
    def test_create_list_delete(self, client, h):
        pids = _create_patterns(client, h)
        mids = _create_members(client, h, pids)
        sid = _create_schedule(client, h)

        r = client.post(f"/api/schedules/{sid}/fixed-assignments", headers=h, json={
            "member_id": mids[0], "date": "2026-07-01", "type": "rest",
        })
        assert r.status_code == 201
        fid = r.json()["id"]

        r = client.get(f"/api/schedules/{sid}/fixed-assignments", headers=h)
        assert len(r.json()) == 1

        r = client.delete(f"/api/schedules/{sid}/fixed-assignments/{fid}", headers=h)
        assert r.status_code == 204

    def test_clear_all(self, client, h):
        pids = _create_patterns(client, h)
        mids = _create_members(client, h, pids)
        sid = _create_schedule(client, h)
        client.post(f"/api/schedules/{sid}/fixed-assignments", headers=h,
                    json={"member_id": mids[0], "date": "2026-07-01", "type": "rest"})
        client.post(f"/api/schedules/{sid}/fixed-assignments", headers=h,
                    json={"member_id": mids[1], "date": "2026-07-02", "type": "rest"})

        r = client.delete(f"/api/schedules/{sid}/fixed-assignments", headers=h)
        assert r.status_code == 204
        r = client.get(f"/api/schedules/{sid}/fixed-assignments", headers=h)
        assert len(r.json()) == 0


# ── Constraints CRUD ──────────────────────────────────────────────────

class TestConstraints:
    def test_create_update_delete(self, client, h):
        pids = _create_patterns(client, h)
        mids = _create_members(client, h, pids)

        r = client.post("/api/constraints", headers=h, json={
            "member_id": mids[0],
            "period_work_days_min": 3, "period_work_days_max": 5,
            "max_consecutive_work_days": 4,
        })
        assert r.status_code == 201
        cid = r.json()["id"]

        r = client.put(f"/api/constraints/{cid}", headers=h, json={
            "member_id": mids[0],
            "period_work_days_min": 4, "period_work_days_max": 6,
        })
        assert r.status_code == 200
        assert r.json()["period_work_days_min"] == 4

        r = client.delete(f"/api/constraints/{cid}", headers=h)
        assert r.status_code == 204

    def test_list(self, client, h):
        pids = _create_patterns(client, h)
        mids = _create_members(client, h, pids)
        client.post("/api/constraints", headers=h, json={
            "member_id": mids[0], "period_work_days_max": 5,
        })
        r = client.get("/api/constraints", headers=h)
        assert r.status_code == 200
        assert len(r.json()) >= 1


# ── Groups + Group Demands ────────────────────────────────────────────

class TestGroups:
    def test_group_crud(self, client, h):
        pids = _create_patterns(client, h)
        mids = _create_members(client, h, pids)

        r = client.post("/api/groups", headers=h, json={
            "name": "Team A", "member_ids": [mids[0], mids[1]],
        })
        assert r.status_code == 201
        gid = r.json()["id"]
        assert len(r.json()["member_ids"]) == 2

        r = client.put(f"/api/groups/{gid}", headers=h, json={
            "name": "Team A Updated", "member_ids": [mids[0]],
        })
        assert r.status_code == 200
        assert r.json()["name"] == "Team A Updated"

        r = client.delete(f"/api/groups/{gid}", headers=h)
        assert r.status_code == 204

    def test_group_demands(self, client, h):
        pids = _create_patterns(client, h)
        mids = _create_members(client, h, pids)
        sid = _create_schedule(client, h)

        r = client.post("/api/groups", headers=h, json={
            "name": "G1", "member_ids": mids,
        })
        gid = r.json()["id"]

        r = client.post(f"/api/schedules/{sid}/group-demands", headers=h, json={
            "date": "2026-07-01", "group_id": gid, "pattern_id": pids[0], "min_count": 1,
        })
        assert r.status_code == 201
        gdid = r.json()["id"]

        r = client.get(f"/api/schedules/{sid}/group-demands", headers=h)
        assert len(r.json()) == 1

        r = client.delete(f"/api/schedules/{sid}/group-demands/{gdid}", headers=h)
        assert r.status_code == 204


# ── Rest Request Lifecycle ────────────────────────────────────────────

class TestRestRequestLifecycle:
    def _setup(self, client, h):
        pids = _create_patterns(client, h)
        mids = _create_members(client, h, pids, names=("Tanaka", "Suzuki"))
        sid = _create_schedule(client, h, rest_request_max_days=2,
                               rest_request_deadline="2026-07-10")
        return pids, mids, sid

    def test_open_creates_drafts_and_tokens(self, client, h):
        _, mids, sid = self._setup(client, h)
        r = client.post(f"/api/schedules/{sid}/rest-requests/open", headers=h)
        assert r.status_code == 200
        assert r.json()["members_count"] == 2

        r = client.get(f"/api/schedules/{sid}/rest-requests", headers=h)
        reqs = r.json()
        assert len(reqs) == 2
        assert all(rq["status"] == "draft" for rq in reqs)

        for mid in mids:
            r = client.get(f"/api/members/{mid}/token", headers=h)
            assert r.json()["personal_token"] is not None

    def test_personal_submit_flow(self, client, h):
        _, mids, sid = self._setup(client, h)
        client.post(f"/api/schedules/{sid}/rest-requests/open", headers=h)

        r = client.get(f"/api/members/{mids[0]}/token", headers=h)
        token = r.json()["personal_token"]

        r = client.get("/api/personal/info", params={"token": token})
        assert r.status_code == 200
        assert r.json()["member_name"] == "Tanaka"
        assert r.json()["schedules"][0]["my_request_status"] == "draft"

        r = client.get(f"/api/personal/schedules/{sid}/rest-request", params={"token": token})
        assert r.status_code == 200
        assert r.json()["rest_request_max_days"] == 2

        r = client.put(f"/api/personal/schedules/{sid}/rest-request",
                       params={"token": token},
                       json={"requested_dates": ["2026-07-02", "2026-07-04"]})
        assert r.status_code == 200
        assert r.json()["requested_dates"] == ["2026-07-02", "2026-07-04"]

        r = client.post(f"/api/personal/schedules/{sid}/rest-request/submit",
                        params={"token": token})
        assert r.status_code == 200
        assert r.json()["status"] == "submitted"

        r = client.put(f"/api/personal/schedules/{sid}/rest-request",
                       params={"token": token},
                       json={"requested_dates": ["2026-07-03"]})
        assert r.status_code == 400

    def test_max_days_enforced(self, client, h):
        _, mids, sid = self._setup(client, h)
        client.post(f"/api/schedules/{sid}/rest-requests/open", headers=h)

        r = client.get(f"/api/members/{mids[0]}/token", headers=h)
        token = r.json()["personal_token"]

        r = client.put(f"/api/personal/schedules/{sid}/rest-request",
                       params={"token": token},
                       json={"requested_dates": ["2026-07-01", "2026-07-02", "2026-07-03"]})
        assert r.status_code == 400

    def test_close_auto_submits_and_creates_fa(self, client, h):
        _, mids, sid = self._setup(client, h)
        client.post(f"/api/schedules/{sid}/rest-requests/open", headers=h)

        r = client.get(f"/api/members/{mids[0]}/token", headers=h)
        token = r.json()["personal_token"]
        client.put(f"/api/personal/schedules/{sid}/rest-request",
                   params={"token": token},
                   json={"requested_dates": ["2026-07-03"]})
        client.post(f"/api/personal/schedules/{sid}/rest-request/submit",
                    params={"token": token})

        r = client.post(f"/api/schedules/{sid}/rest-requests/close", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["auto_submitted"] == 1
        assert data["fixed_assignments_created"] == 1

        r = client.get(f"/api/schedules/{sid}/fixed-assignments", headers=h)
        fas = r.json()
        assert len(fas) == 1
        assert fas[0]["type"] == "rest"
        assert fas[0]["member_id"] == mids[0]

    def test_invalid_token_rejected(self, client):
        r = client.get("/api/personal/info", params={"token": "invalid-uuid"})
        assert r.status_code == 401


# ── Multi-Tenant Isolation (expanded) ─────────────────────────────────

class TestTenantIsolationExpanded:
    def test_patterns_isolated(self, client):
        h1 = _register_and_login(client, "a@x.com", tenant="X")
        h2 = _register_and_login(client, "b@y.com", tenant="Y")

        client.post("/api/patterns", headers=h1, json={
            "name": "XOnly", "type": "work",
            "start_time": "09:00", "end_time": "17:00", "work_hours": 7,
        })
        r = client.get("/api/patterns", headers=h2)
        assert all(p["name"] != "XOnly" for p in r.json())

    def test_schedules_isolated(self, client):
        h1 = _register_and_login(client, "a@x.com", tenant="X")
        h2 = _register_and_login(client, "b@y.com", tenant="Y")

        sid = _create_schedule(client, h1, name="X-Schedule")
        r = client.get("/api/schedules", headers=h2)
        assert all(s["name"] != "X-Schedule" for s in r.json())

        r = client.get(f"/api/schedules/{sid}", headers=h2)
        assert r.status_code == 404

    def test_constraints_isolated(self, client):
        h1 = _register_and_login(client, "a@x.com", tenant="X")
        h2 = _register_and_login(client, "b@y.com", tenant="Y")

        pids = _create_patterns(client, h1)
        mids = _create_members(client, h1, pids, names=("XMember",))

        r = client.post("/api/constraints", headers=h1, json={
            "member_id": mids[0], "period_work_days_max": 5,
        })
        cid = r.json()["id"]

        r = client.get(f"/api/constraints/{cid}", headers=h2)
        assert r.status_code == 404

    def test_rest_requests_isolated(self, client):
        h1 = _register_and_login(client, "a@x.com", tenant="X")
        h2 = _register_and_login(client, "b@y.com", tenant="Y")

        _create_patterns(client, h1)
        _create_members(client, h1, [], names=("XM",))
        sid = _create_schedule(client, h1)

        r = client.post(f"/api/schedules/{sid}/rest-requests/open", headers=h2)
        assert r.status_code == 404

    def test_personal_token_tenant_boundary(self, client):
        h1 = _register_and_login(client, "a@x.com", tenant="X")
        h2 = _register_and_login(client, "b@y.com", tenant="Y")

        pids1 = _create_patterns(client, h1)
        mids1 = _create_members(client, h1, pids1, names=("XMember",))

        pids2 = _create_patterns(client, h2, names=("Y-Day",))
        mids2 = _create_members(client, h2, pids2, names=("YMember",))
        sid2 = _create_schedule(client, h2, name="Y-Sched")
        client.post(f"/api/schedules/{sid2}/rest-requests/open", headers=h2)

        r = client.get(f"/api/members/{mids1[0]}/token", headers=h1)
        token_x = r.json()["personal_token"]
        if token_x is None:
            client.post(f"/api/members/{mids1[0]}/token", headers=h1)
            r = client.get(f"/api/members/{mids1[0]}/token", headers=h1)
            token_x = r.json()["personal_token"]

        r = client.get(f"/api/personal/schedules/{sid2}/rest-request",
                       params={"token": token_x})
        assert r.status_code == 404


# ── Security Edge Cases ───────────────────────────────────────────────

class TestSecurity:
    def test_no_auth_returns_401(self, client):
        for path in ["/api/members", "/api/patterns", "/api/schedules",
                     "/api/constraints", "/api/groups"]:
            r = client.get(path)
            assert r.status_code == 401, f"{path} should require auth"

    def test_invalid_jwt(self, client):
        r = client.get("/api/members",
                       headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401

    def test_expired_token_rejected(self, client):
        from api.services.auth import create_access_token
        import os
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
        _register_and_login(client, "exp@test.com")
        from jose import jwt
        from api.config import SECRET_KEY, ALGORITHM
        token = jwt.encode({"sub": "fakeid", "tid": "faketid", "exp": 0},
                           SECRET_KEY, algorithm=ALGORITHM)
        r = client.get("/api/members", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_double_submit_rejected(self, client, h):
        pids = _create_patterns(client, h)
        mids = _create_members(client, h, pids)
        sid = _create_schedule(client, h, rest_request_max_days=2)
        client.post(f"/api/schedules/{sid}/rest-requests/open", headers=h)

        r = client.get(f"/api/members/{mids[0]}/token", headers=h)
        token = r.json()["personal_token"]

        client.put(f"/api/personal/schedules/{sid}/rest-request",
                   params={"token": token},
                   json={"requested_dates": ["2026-07-01"]})
        client.post(f"/api/personal/schedules/{sid}/rest-request/submit",
                    params={"token": token})

        r = client.post(f"/api/personal/schedules/{sid}/rest-request/submit",
                        params={"token": token})
        assert r.status_code == 400

    def test_submit_after_close_rejected(self, client, h):
        pids = _create_patterns(client, h)
        mids = _create_members(client, h, pids)
        sid = _create_schedule(client, h, rest_request_max_days=2)
        client.post(f"/api/schedules/{sid}/rest-requests/open", headers=h)

        r = client.get(f"/api/members/{mids[0]}/token", headers=h)
        token = r.json()["personal_token"]

        client.post(f"/api/schedules/{sid}/rest-requests/close", headers=h)

        r = client.put(f"/api/personal/schedules/{sid}/rest-request",
                       params={"token": token},
                       json={"requested_dates": ["2026-07-01"]})
        assert r.status_code == 400
