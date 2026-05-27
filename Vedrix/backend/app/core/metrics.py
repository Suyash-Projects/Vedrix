"""
Prometheus metrics for monitoring.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import APIRouter, Response
import time

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

# Business metrics
interviews_started = Counter(
    "interviews_started_total",
    "Total interviews started"
)

interviews_completed = Counter(
    "interviews_completed_total",
    "Total interviews completed"
)

interviews_duration = Histogram(
    "interview_duration_seconds",
    "Interview duration in seconds"
)

active_interviews = Gauge(
    "active_interviews",
    "Number of currently active interviews"
)

# AI API metrics
ai_api_calls = Counter(
    "ai_api_calls_total",
    "Total AI API calls",
    ["provider", "status"]
)

ai_api_duration = Histogram(
    "ai_api_duration_seconds",
    "AI API call duration in seconds",
    ["provider"]
)

# Database metrics
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"]
)

# Active WebSocket connections
active_websocket_connections = Gauge(
    "active_websocket_connections",
    "Number of currently active WebSocket connections"
)

# Email metrics
email_sent_total = Counter(
    "email_sent_total",
    "Total emails sent",
    ["status"]
)

# PDF generation metrics
pdf_generated_total = Counter(
    "pdf_generated_total",
    "Total PDFs generated"
)


router = APIRouter()


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


# Context manager for timing requests
class RequestTimer:
    def __init__(self, method: str, endpoint: str):
        self.method = method
        self.endpoint = endpoint
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        http_request_duration.labels(
            method=self.method,
            endpoint=self.endpoint
        ).observe(duration)

    def set_status(self, status: int):
        http_requests_total.labels(
            method=self.method,
            endpoint=self.endpoint,
            status=status
        ).inc()