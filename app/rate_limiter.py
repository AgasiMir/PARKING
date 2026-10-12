import random
from time import time

from redis import ResponseError
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.decorators import retry


class RateLimiter:
    def __init__(self, redis: Redis):
        self._redis = redis

    @retry(exceptions=(RedisConnectionError, RedisTimeoutError, ResponseError))
    async def is_limited(
        self,
        ip_address: str,
        endpoint: str,
        max_requests: int,
        window_seconds: int,
    ) -> bool:
        key = f"rate_limit:{endpoint}:{ip_address}"

        current_ms = time() * 1000
        window_start_ms = current_ms - window_seconds * 1000

        current_request = f"{current_ms}-{random.randint(0, 100_000)}"

        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.zremrangebyscore(name=key, min=0, max=window_start_ms)

            # Получения числа элементов в сортированном множестве по ключу
            await pipe.zcard(name=key)

            await pipe.zadd(name=key, mapping={current_request: current_ms})

            # Очистка сортированного множества по TTL на основе ключа и параметра window_seconds
            await pipe.expire(name=key, time=window_seconds)

            res = await pipe.execute()

        _, current_count, _, _ = res
        return current_count >= max_requests
