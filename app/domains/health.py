from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(prefix="/health", tags=["health 📊📈"])


@router.get("/metrics")
async def get_metrics():
    """
    Эндпоинт для сбора метрик Prometheus.
    Доступ: GET /metrics
    Content-Type: text/plain
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
