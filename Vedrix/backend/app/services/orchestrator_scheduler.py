"""
Orchestrator Scheduler — Periodic workflow checks using asyncio task loop.

Runs `OrchestratorService.run_scheduled_checks()` every 15 minutes (configurable).
Follows the same pattern as `session_cleanup.py` for lifecycle management.

Design: Section 8 (Orchestrator)
Requirements: 8.4, 8.5, 8.7, 8.10
"""
import asyncio
import logging
from typing import Optional

from app.db.session import async_session

logger = logging.getLogger(__name__)


class OrchestratorScheduler:
    """
    Manages the periodic execution of orchestrator workflow checks.

    Checks performed every interval:
    - 48h invite reminders for candidates stuck in "invited"
    - 24h pre-interview reminders for candidates in "scheduled"
    - Escalation of stale "evaluated" states after 5 business days
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self, interval_seconds: int = 900) -> None:
        """Start the periodic orchestrator checks loop (default: every 15 minutes)."""
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop(interval_seconds))
        logger.info(
            f"Orchestrator scheduler started (interval: {interval_seconds}s / "
            f"{interval_seconds // 60} min)"
        )

    async def stop(self) -> None:
        """Stop the orchestrator scheduler loop."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Orchestrator scheduler stopped")

    async def _run_loop(self, interval_seconds: int) -> None:
        """Internal loop that runs scheduled checks at the configured interval."""
        # Wait one interval before the first run to let the system stabilize
        await asyncio.sleep(interval_seconds)

        while self._is_running:
            try:
                await self._execute_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Orchestrator scheduled checks failed: {e}")

            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break

    async def _execute_checks(self) -> None:
        """Execute the orchestrator's scheduled workflow checks."""
        from app.services.orchestrator_service import OrchestratorService

        orchestrator = OrchestratorService()

        async with async_session() as db:
            await orchestrator.run_scheduled_checks(db=db)

        logger.info("Orchestrator scheduled checks completed successfully")


# Global instance
orchestrator_scheduler = OrchestratorScheduler()
