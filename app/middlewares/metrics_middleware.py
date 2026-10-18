"""
Middleware для сбора метрик Prometheus:
- REQUESTS_TOTAL: общее количество HTTP-запросов
- REQUEST_DURATION: время выполнения запроса (в секундах)
- ACTIVE_REQUESTS: количество активных запросов (in-progress)
"""

import time

from fastapi import Request

from app.prom_metrics import ACTIVE_REQUESTS, REQUEST_DURATION, REQUESTS_TOTAL


async def metrics_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    method = request.method
    status_code = "500"

    # request.url.path всегда существует; route может быть не заполнен до вызова call_next()
    route = request.scope.get("route")
    endpoint = getattr(route, "path", request.url.path)

    active_labels = {"method": method, "endpoint": endpoint}
    ACTIVE_REQUESTS.labels(**active_labels).inc()

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except Exception:
        raise
    finally:
        duration = time.perf_counter() - start_time

        request_labels = {
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
        }

        REQUEST_DURATION.labels(**request_labels).observe(duration)
        REQUESTS_TOTAL.labels(**request_labels).inc()

        ACTIVE_REQUESTS.labels(**active_labels).dec()
