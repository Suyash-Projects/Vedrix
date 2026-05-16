"""
Session Cleanup Service for Vedrix AI Interview System.

Handles:
- Session timeout detection (30 min inactivity)
- Abandoned session cleanup (24h)
- Periodic cleanup cron job
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Session timeout settings
SESSION_INACTIVE_TIMEOUT_MINUTES = 30
SESSION_ABANDONED_HOURS = 24


class SessionCleanupService:
    """
    Manages interview session lifecycle:
    - Tracks active sessions and their last activity timestamp
    - Detects inactive sessions and marks them as expired
    - Cleans up abandoned sessions after 24 hours
    """

    def __init__(self):
        self._last_activity: dict[str, datetime] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False

    def record_activity(self, session_id: str):
        """Record that a session was active."""
        self._last_activity[session_id] = datetime.now(timezone.utc)

    def get_last_activity(self, session_id: str) -> Optional[datetime]:
        """Get the last activity timestamp for a session."""
        return self._last_activity.get(session_id)

    def is_session_active(self, session_id: str) -> bool:
        """Check if a session is still active (within timeout window)."""
        last = self._last_activity.get(session_id)
        if not last:
            return False
        elapsed = datetime.now(timezone.utc) - last
        return elapsed.total_seconds() < SESSION_INACTIVE_TIMEOUT_MINUTES * 60

    def remove_session(self, session_id: str):
        """Remove a session from tracking."""
        self._last_activity.pop(session_id, None)

    async def start_cleanup_loop(self, interval_seconds: int = 300):
        """Start the periodic cleanup loop (runs every 5 minutes by default)."""
        if self._is_running:
            return
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop(interval_seconds))
        logger.info(f"Session cleanup service started (interval: {interval_seconds}s)")

    async def stop_cleanup_loop(self):
        """Stop the cleanup loop."""
        self._is_running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Session cleanup service stopped")

    async def _cleanup_loop(self, interval_seconds: int):
        """Internal cleanup loop."""
        while self._is_running:
            try:
                await self._cleanup_inactive_sessions()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
                await asyncio.sleep(interval_seconds)

    async def _cleanup_inactive_sessions(self):
        """
        Check for inactive sessions and mark them as expired.
        Also clean up abandoned sessions older than 24 hours.
        """
        now = datetime.now(timezone.utc)
        inactive_threshold = now - timedelta(minutes=SESSION_INACTIVE_TIMEOUT_MINUTES)
        abandoned_threshold = now - timedelta(hours=SESSION_ABANDONED_HOURS)

        expired_sessions = []
        abandoned_sessions = []

        for session_id, last_activity in list(self._last_activity.items()):
            if last_activity < inactive_threshold:
                expired_sessions.append(session_id)
            if last_activity < abandoned_threshold:
                abandoned_sessions.append(session_id)

        # Remove expired sessions from tracking
        for session_id in expired_sessions:
            logger.info(f"Session {session_id} expired due to inactivity")
            self.remove_session(session_id)

        # Remove abandoned sessions
        for session_id in abandoned_sessions:
            logger.info(f"Session {session_id} abandoned, cleaning up")
            self.remove_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} inactive sessions")
        if abandoned_sessions:
            logger.info(f"Cleaned up {len(abandoned_sessions)} abandoned sessions")


# Global instance
session_cleanup = SessionCleanupService()
