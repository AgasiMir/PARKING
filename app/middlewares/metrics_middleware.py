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
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    status_code = "500"

    # Увеличиваем active requests — только с method и endpoint
    active_labels = {"method": method, "endpoint": endpoint}
    ACTIVE_REQUESTS.labels(**active_labels).inc()

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except Exception:
        raise
    finally:
        # Время выполнения и счётчик запросов — с status_code
        duration = time.time() - start_time
        request_labels = {
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
        }

        REQUEST_DURATION.labels(**request_labels).observe(duration)
        REQUESTS_TOTAL.labels(**request_labels).inc()

        # Уменьшаем active — снова без status_code
        ACTIVE_REQUESTS.labels(**active_labels).dec()
