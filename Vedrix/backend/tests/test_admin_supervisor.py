"""Integration tests for AI Supervisor Admin REST API endpoints.

Tests the 5 supervisor endpoints in admin.py:
  - GET /api/v1/admin/supervisor/active-sessions
  - GET /api/v1/admin/supervisor/sessions/{session_id}
  - GET /api/v1/admin/supervisor/sessions/{session_id}/timeline
  - POST /api/v1/admin/supervisor/sessions/{session_id}/override
  - GET /api/v1/admin/supervisor/stats

Requires conftest fixtures: client, admin_headers, db_session, admin_user.
"""

from __future__ import annotations

import time
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from app.services.supervisor_service import (
    supervisor_registry,
    SupervisorObservation,
    SupervisorAction,
    SupervisorState,
)


# ═════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure clean registry before and after each test."""
    for s in list(supervisor_registry._sessions.keys()):
        supervisor_registry.unregister(s)
    yield
    for s in list(supervisor_registry._sessions.keys()):
        supervisor_registry.unregister(s)


@pytest.fixture
def seeded_registry():
    """Seed the supervisor_registry with sample sessions for testing."""
    # Session 1: active, suggest mode, with observations
    s1 = supervisor_registry.register("sess-001", control_mode="suggest")
    s1.difficulty_analysis.current_difficulty = "medium"
    s1.difficulty_analysis.recommended_difficulty = "hard"
    s1.performance_trend.trend = "improving"
    s1.duration_analysis.total_elapsed_seconds = 600
    s1.add_observation(
        SupervisorObservation(
            observation_type="duration_alert",
            severity="warning",
            message="Question taking too long",
            details={"duration": 310},
        )
    )
    s1.add_observation(
        SupervisorObservation(
            observation_type="difficulty_anomaly",
            severity="info",
            message="Difficulty adjustment recommended",
        )
    )

    # Session 2: active, auto mode
    s2 = supervisor_registry.register("sess-002", control_mode="auto")
    s2.performance_trend.trend = "declining"
    s2.performance_trend.fatigue_detected = True
    s2.duration_analysis.total_elapsed_seconds = 1800

    # Session 3: inactive (not returned in active-sessions)
    s3 = supervisor_registry.register("sess-003", control_mode="monitor")
    s3.is_active = False

    yield
    # cleanup is handled by autouse fixture


class TestSupervisorEndpoints:
    """Test all 5 supervisor REST endpoints."""

    API_PREFIX = "/api/v1/admin/supervisor"

    # ── GET /active-sessions ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_active_sessions_returns_only_active(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.get(f"{self.API_PREFIX}/active-sessions", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2  # sess-001 and sess-002 are active
        session_ids = [s["session_id"] for s in data]
        assert "sess-001" in session_ids
        assert "sess-002" in session_ids
        assert "sess-003" not in session_ids  # inactive

    @pytest.mark.asyncio
    async def test_get_active_sessions_structure(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.get(f"{self.API_PREFIX}/active-sessions", headers=admin_headers)
        assert resp.status_code == 200
        session = resp.json()[0]
        assert "session_id" in session
        assert "control_mode" in session
        assert "duration_seconds" in session
        assert "difficulty_analysis" in session
        assert "performance_trend" in session
        assert "observations_count" in session
        assert "paused" in session

    @pytest.mark.asyncio
    async def test_get_active_sessions_sorted_by_duration(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.get(f"{self.API_PREFIX}/active-sessions", headers=admin_headers)
        data = resp.json()
        durations = [s["duration_seconds"] for s in data]
        assert durations == sorted(durations, reverse=True)

    @pytest.mark.asyncio
    async def test_get_active_sessions_requires_admin(self, client: AsyncClient, auth_headers):
        """Non-admin user should get 403."""
        resp = await client.get(f"{self.API_PREFIX}/active-sessions", headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_get_active_sessions_empty(self, client: AsyncClient, admin_headers, clean_registry):
        resp = await client.get(f"{self.API_PREFIX}/active-sessions", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    # ── GET /sessions/{id} ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_session_detail(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.get(f"{self.API_PREFIX}/sessions/sess-001", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-001"
        assert data["control_mode"] == "suggest"
        assert "observations" in data
        assert len(data["observations"]) == 2
        assert "difficulty_analysis" in data
        assert "performance_trend" in data
        assert "duration_analysis" in data
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_session_detail_not_found(self, client: AsyncClient, admin_headers, clean_registry):
        resp = await client.get(f"{self.API_PREFIX}/sessions/nonexistent", headers=admin_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_session_detail_checks_observations(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.get(f"{self.API_PREFIX}/sessions/sess-001", headers=admin_headers)
        data = resp.json()
        obs_types = [o["observation_type"] for o in data["observations"]]
        assert "duration_alert" in obs_types
        assert "difficulty_anomaly" in obs_types

    # ── GET /sessions/{id}/timeline ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_timeline(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.get(f"{self.API_PREFIX}/sessions/sess-001/timeline", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        entry = data[0]
        assert "timestamp" in entry
        assert "type" in entry
        assert "severity" in entry
        assert "message" in entry

    @pytest.mark.asyncio
    async def test_get_timeline_with_limit(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.get(
            f"{self.API_PREFIX}/sessions/sess-001/timeline?limit=1",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_get_timeline_not_found(self, client: AsyncClient, admin_headers, clean_registry):
        resp = await client.get(f"{self.API_PREFIX}/sessions/nonexistent/timeline", headers=admin_headers)
        assert resp.status_code == 404

    # ── POST /sessions/{id}/override ──────────────────────────────────────

    @pytest.mark.asyncio
    async def test_override_set_control_mode(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.post(
            f"{self.API_PREFIX}/sessions/sess-001/override",
            headers=admin_headers,
            json={"action": "set_control_mode", "mode": "auto", "reason": "Testing override"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        # Verify the state changed
        state = supervisor_registry.get("sess-001")
        assert state.control_mode == "auto"

    @pytest.mark.asyncio
    async def test_override_pause(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.post(
            f"{self.API_PREFIX}/sessions/sess-001/override",
            headers=admin_headers,
            json={"action": "pause", "reason": "Testing pause"},
        )
        assert resp.status_code == 200
        state = supervisor_registry.get("sess-001")
        assert state.paused is True

    @pytest.mark.asyncio
    async def test_override_resume(self, client: AsyncClient, admin_headers, seeded_registry):
        # First pause
        supervisor_registry.pause_session("sess-001")
        resp = await client.post(
            f"{self.API_PREFIX}/sessions/sess-001/override",
            headers=admin_headers,
            json={"action": "resume", "reason": "Testing resume"},
        )
        assert resp.status_code == 200
        state = supervisor_registry.get("sess-001")
        assert state.paused is False

    @pytest.mark.asyncio
    async def test_override_records_observation(self, client: AsyncClient, admin_headers, seeded_registry):
        prev_count = len(supervisor_registry.get("sess-001").observations)
        resp = await client.post(
            f"{self.API_PREFIX}/sessions/sess-001/override",
            headers=admin_headers,
            json={"action": "pause", "reason": "Admin requested pause"},
        )
        assert resp.status_code == 200
        state = supervisor_registry.get("sess-001")
        assert len(state.observations) == prev_count + 1
        assert state.observations[-1].observation_type == "admin_override"

    @pytest.mark.asyncio
    async def test_override_unknown_action_does_not_error(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.post(
            f"{self.API_PREFIX}/sessions/sess-001/override",
            headers=admin_headers,
            json={"action": "unknown_action", "reason": "Testing unknown"},
        )
        assert resp.status_code == 200  # It still records the observation

    @pytest.mark.asyncio
    async def test_override_requires_admin(self, client: AsyncClient, auth_headers, seeded_registry):
        resp = await client.post(
            f"{self.API_PREFIX}/sessions/sess-001/override",
            headers=auth_headers,
            json={"action": "pause", "reason": "Testing"},
        )
        assert resp.status_code == 403

    # ── GET /stats ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_stats(self, client: AsyncClient, admin_headers, seeded_registry):
        resp = await client.get(f"{self.API_PREFIX}/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_sessions"] == 2
        assert data["sessions_with_alerts"] == 1  # only sess-001 has duration_alert
        assert data["auto_mode_sessions"] == 1
        assert data["suggest_mode_sessions"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, client: AsyncClient, admin_headers, clean_registry):
        resp = await client.get(f"{self.API_PREFIX}/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_sessions"] == 0
        assert data["sessions_with_alerts"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_requires_admin(self, client: AsyncClient, auth_headers):
        resp = await client.get(f"{self.API_PREFIX}/stats", headers=auth_headers)
        assert resp.status_code == 403
