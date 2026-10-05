from prometheus_client import Counter, Gauge, Histogram

REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Общее количество HTTP-запросов",
    ["method", "endpoint", "status_code"],
)

ACTIVE_CONNECTIONS = Gauge(
    "active_connections",
    "Current number of active connections",
    ["app"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Время выполнения HTTP-запросов",
    ["method", "endpoint", "status_code"],
    buckets=[0.1, 0.3, 0.5, 1.0, 2.0, 5.0],
)

ACTIVE_REQUESTS = Gauge(
    "active_requests",
    "Количество активных HTTP-запросов",
    ["method", "endpoint"],
)
