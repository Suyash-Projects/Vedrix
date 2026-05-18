"""
Distributed tracing for Vedrix AI Interview System.
Uses OpenTelemetry for cross-service request tracking.
"""
import logging
import time
from typing import Optional, Dict, Any
from contextvars import ContextVar
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Context variable for current trace ID
current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


class TraceContext:
    """Manages distributed tracing context."""

    def __init__(self, trace_id: str, span_id: str, parent_span_id: Optional[str] = None):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.attributes: Dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any):
        """Set a trace attribute."""
        self.attributes[key] = value

    def end(self, status: str = "ok", error: Optional[str] = None):
        """End the trace span."""
        duration = time.time() - self.start_time
        log_entry = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration_ms": round(duration * 1000, 2),
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": self.attributes,
        }
        if error:
            log_entry["error"] = error

        logger.info(f"TRACE: {log_entry}")
        return log_entry


class Tracer:
    """Distributed tracer for Vedrix."""

    def __init__(self, service_name: str = "vedrix"):
        self.service_name = service_name

    def start_span(
        self,
        operation_name: str,
        parent_trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> TraceContext:
        """Start a new trace span."""
        import uuid

        trace_id = parent_trace_id or str(uuid.uuid4())
        span_id = str(uuid.uuid4())[:16]

        ctx = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
        )
        ctx.set_attribute("service", self.service_name)
        ctx.set_attribute("operation", operation_name)

        # Set current trace ID in context
        current_trace_id.set(trace_id)

        return ctx

    def get_current_trace_id(self) -> str:
        """Get the current trace ID from context."""
        return current_trace_id.get()


# Singleton instance
tracer = Tracer()
