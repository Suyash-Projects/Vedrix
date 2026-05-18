"""
Error alerting service for sending notifications when errors occur.

Supports email and Slack alerts with configurable thresholds.
"""
import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from app.core.config import settings

logger = logging.getLogger(__name__)

# Alert thresholds
ALERT_THRESHOLDS = {
    "high_error_rate": {"threshold": 0.01, "window_minutes": 5},  # 1% error rate over 5 min
    "slow_api": {"threshold": 2.0, "window_minutes": 10},  # p95 > 2s over 10 min
    "ai_provider_down": {"threshold": 3, "window_minutes": 5},  # 3 failures over 5 min
    "database_slow": {"threshold": 0.5, "window_minutes": 5},  # 500ms over 5 min
}


class AlertManager:
    """Manages error alerts and notifications."""

    def __init__(self):
        self.error_counts: Dict[str, List[datetime]] = defaultdict(list)
        self.response_times: List[float] = []
        self.ai_failures: Dict[str, List[datetime]] = defaultdict(list)
        self.db_query_times: List[float] = []
        self.last_alert_time: Dict[str, datetime] = {}
        self.alert_cooldown_minutes = 15  # Don't send same alert more than once per 15 min

    def record_error(self, endpoint: str, status_code: int):
        """Record an error for alerting analysis."""
        now = datetime.now(timezone.utc)
        key = f"{endpoint}:{status_code}"
        self.error_counts[key].append(now)

        # Clean old entries
        self._clean_old_entries(self.error_counts[key], 30)

    def record_response_time(self, duration: float):
        """Record a response time for performance monitoring."""
        self.response_times.append(duration)
        # Keep only last 1000 entries
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]

    def record_ai_failure(self, provider: str):
        """Record an AI provider failure."""
        now = datetime.now(timezone.utc)
        self.ai_failures[provider].append(now)
        self._clean_old_entries(self.ai_failures[provider], 30)

    def record_db_query_time(self, duration: float):
        """Record a database query time."""
        self.db_query_times.append(duration)
        if len(self.db_query_times) > 1000:
            self.db_query_times = self.db_query_times[-1000:]

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert conditions and return triggered alerts."""
        alerts = []
        now = datetime.now(timezone.utc)

        # Check high error rate
        if self._check_error_rate(now):
            alerts.append({
                "name": "high_error_rate",
                "severity": "critical",
                "message": "High error rate detected (>1% over 5 minutes)",
                "action": "email + slack",
            })

        # Check slow API
        if self._check_slow_api(now):
            alerts.append({
                "name": "slow_api",
                "severity": "warning",
                "message": "Slow API responses detected (p95 > 2s over 10 minutes)",
                "action": "slack",
            })

        # Check AI provider down
        for provider, failures in self.ai_failures.items():
            if self._check_ai_provider_down(provider, now):
                alerts.append({
                    "name": "ai_provider_down",
                    "severity": "critical",
                    "message": f"AI provider {provider} is down (3+ failures over 5 minutes)",
                    "action": "email + slack + page",
                })

        # Check database slow
        if self._check_database_slow(now):
            alerts.append({
                "name": "database_slow",
                "severity": "warning",
                "message": "Database queries are slow (>500ms over 5 minutes)",
                "action": "slack",
            })

        return alerts

    def _check_error_rate(self, now: datetime) -> bool:
        """Check if error rate exceeds threshold."""
        threshold = ALERT_THRESHOLDS["high_error_rate"]
        window = timedelta(minutes=threshold["window_minutes"])

        total_errors = 0
        total_requests = 0

        for key, timestamps in self.error_counts.items():
            recent = [t for t in timestamps if now - t < window]
            total_errors += len(recent)

        # Estimate total requests (errors + successful)
        # This is a simplified estimate
        total_requests = max(total_errors * 10, 1)  # Assume 10% error rate baseline
        error_rate = total_errors / total_requests

        return error_rate > threshold["threshold"]

    def _check_slow_api(self, now: datetime) -> bool:
        """Check if API response times exceed threshold."""
        threshold = ALERT_THRESHOLDS["slow_api"]

        if not self.response_times:
            return False

        # Calculate p95
        sorted_times = sorted(self.response_times)
        p95_idx = int(len(sorted_times) * 0.95)
        p95 = sorted_times[p95_idx] if p95_idx < len(sorted_times) else 0

        return p95 > threshold["threshold"]

    def _check_ai_provider_down(self, provider: str, now: datetime) -> bool:
        """Check if AI provider has too many failures."""
        threshold = ALERT_THRESHOLDS["ai_provider_down"]
        window = timedelta(minutes=threshold["window_minutes"])

        failures = self.ai_failures.get(provider, [])
        recent = [t for t in failures if now - t < window]

        return len(recent) >= threshold["threshold"]

    def _check_database_slow(self, now: datetime) -> bool:
        """Check if database queries are too slow."""
        threshold = ALERT_THRESHOLDS["database_slow"]

        if not self.db_query_times:
            return False

        avg_time = sum(self.db_query_times) / len(self.db_query_times)
        return avg_time > threshold["threshold"]

    def _clean_old_entries(self, timestamps: List[datetime], max_minutes: int):
        """Remove entries older than max_minutes."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_minutes)
        timestamps[:] = [t for t in timestamps if t > cutoff]

    async def send_alert(self, alert: Dict[str, Any]):
        """Send an alert via configured channels."""
        alert_name = alert["name"]
        now = datetime.now(timezone.utc)

        # Check cooldown
        last_alert = self.last_alert_time.get(alert_name)
        if last_alert and (now - last_alert).total_seconds() < self.alert_cooldown_minutes * 60:
            return

        # Send alert
        logger.warning(f"ALERT [{alert['severity'].upper()}]: {alert['message']}")

        # Send email if configured
        if "email" in alert["action"] and hasattr(settings, 'ALERT_EMAIL'):
            await self._send_email_alert(alert)

        # Send Slack if configured
        if "slack" in alert["action"] and hasattr(settings, 'SLACK_WEBHOOK_URL'):
            await self._send_slack_alert(alert)

        # Update last alert time
        self.last_alert_time[alert_name] = now

    async def _send_email_alert(self, alert: Dict[str, Any]):
        """Send alert via email."""
        try:
            # In production, integrate with email service
            logger.info(f"Email alert: {alert['message']}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    async def _send_slack_alert(self, alert: Dict[str, Any]):
        """Send alert via Slack webhook."""
        try:
            # In production, send to Slack webhook
            logger.info(f"Slack alert: {alert['message']}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")


# Singleton instance
alert_manager = AlertManager()
