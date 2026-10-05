from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from loguru import logger

SKIP_PATHS = {"/health/metrics", "/favicon.ico"}
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def _patch_record(record):
    record["extra"].setdefault("request_id", request_id_ctx.get())
    return record


logger = logger.patch(_patch_record)


def setup_logging():
    logger.remove()
    logger.add(
        sink="logs/logs.log",
        rotation="10 MB",
        compression="zip",
        retention="30 days",
        encoding="utf-8",
        catch=True,
        serialize=True,
        enqueue=True,
        level="INFO",
        backtrace=True,
        diagnose=False,  # diagnose=True утекает значения переменных!
    )


async def log_requests(request: Request, call_next):
    if request.url.path in SKIP_PATHS:
        return await call_next(request)

    request_id = str(uuid4())
    token = request_id_ctx.set(request_id)
    start = perf_counter()
    response = None
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled exception",
            path=request.url.path,
            method=request.method,
        )
        raise
    finally:
        # логируем успешный ответ ДО сброса контекста
        if response is not None:
            log_data = {
                "event": "request",
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "process_time_ms": round((perf_counter() - start) * 1000, 2),
                "client_ip": request.client.host if request.client else None,
                "user_agent": (request.headers.get("user-agent") or "")[:500],
            }
            level = (
                "ERROR"
                if response.status_code >= 500
                else "WARNING"
                if response.status_code >= 400
                else "INFO"
            )
            logger.bind(**log_data).log(level, "request")
        request_id_ctx.reset(token)

    response.headers["X-Request-ID"] = request_id
    return response
