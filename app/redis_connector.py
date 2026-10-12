from functools import cache

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.config import get_settings
from app.decorators import retry

settings = get_settings()


@cache
def get_redis() -> Redis:
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
    )


@retry(
    retries=5,
    delay=1,
    backoff_factor=1.0,
    exceptions=(RedisConnectionError, RedisTimeoutError),
)
async def ping_redis(redis: Redis) -> None:
    await redis.ping()
