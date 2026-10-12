from unittest.mock import AsyncMock, MagicMock, patch

from redis import ResponseError
from redis.exceptions import ConnectionError as RedisConnectionError

from app.rate_limiter import RateLimiter


class FakePipeline:
    """Фейковый pipeline с явным async context manager."""

    def __init__(self, execute_result: list, execute_side_effect: list | None = None):
        self.execute_result = execute_result
        self.execute_side_effect = list(execute_side_effect) if execute_side_effect else []
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def zremrangebyscore(self, **kwargs):
        self.calls.append(("zremrangebyscore", kwargs))

    async def zcard(self, **kwargs):
        self.calls.append(("zcard", kwargs))

    async def zadd(self, **kwargs):
        self.calls.append(("zadd", kwargs))

    async def expire(self, **kwargs):
        self.calls.append(("expire", kwargs))

    async def execute(self):
        self.calls.append(("execute", {}))
        if self.execute_side_effect:
            item = self.execute_side_effect.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return self.execute_result


def make_limiter(execute_result: list, execute_side_effect: list | None = None):
    pipe = FakePipeline(execute_result, execute_side_effect)
    redis = MagicMock()
    redis.pipeline.return_value = pipe
    return RateLimiter(redis=redis), redis, pipe


async def test_is_limited_false_when_below_limit():
    limiter, _, _ = make_limiter([0, 4, 1, 1])  # zcard = 4 < max_requests = 5
    assert await limiter.is_limited("127.0.0.1", "parking_list", 5, 5) is False


async def test_is_limited_true_when_at_limit():
    limiter, _, _ = make_limiter([0, 5, 1, 1])  # zcard = 5 >= max_requests = 5
    assert await limiter.is_limited("127.0.0.1", "parking_list", 5, 5) is True


async def test_is_limited_true_when_over_limit():
    limiter, _, _ = make_limiter([0, 7, 1, 1])  # zcard = 7 > max_requests = 5
    assert await limiter.is_limited("127.0.0.1", "parking_list", 5, 5) is True


async def test_is_limited_calls_pipeline_commands():
    limiter, redis, pipe = make_limiter([0, 1, 1, 1])
    await limiter.is_limited("127.0.0.1", "parking_list", 5, 5)

    redis.pipeline.assert_called_once_with(transaction=True)
    assert [name for name, _ in pipe.calls] == [
        "zremrangebyscore",
        "zcard",
        "zadd",
        "expire",
        "execute",
    ]


async def test_is_limited_uses_correct_key_and_window():
    limiter, _, pipe = make_limiter([0, 1, 1, 1])

    with patch("app.rate_limiter.time", return_value=1_000_000.0):
        await limiter.is_limited("127.0.0.1", "parking_list", 5, 5)

    key = "rate_limit:parking_list:127.0.0.1"
    assert ("zremrangebyscore", {"name": key, "min": 0, "max": 999_995_000}) in pipe.calls
    assert ("zcard", {"name": key}) in pipe.calls
    assert ("expire", {"name": key, "time": 5}) in pipe.calls


async def test_is_limited_zadd_mapping():
    limiter, _, pipe = make_limiter([0, 1, 1, 1])

    with (
        patch("app.rate_limiter.time", return_value=1_000_000.0),
        patch("app.rate_limiter.random.randint", return_value=42),
    ):
        await limiter.is_limited("127.0.0.1", "parking_list", 5, 5)

    key = "rate_limit:parking_list:127.0.0.1"
    assert ("zadd", {"name": key, "mapping": {"1000000000.0-42": 1_000_000_000.0}}) in pipe.calls


async def test_is_limited_retries_on_redis_connection_error():
    limiter, _, pipe = make_limiter(
        [0, 1, 1, 1],
        execute_side_effect=[RedisConnectionError("boom")],
    )

    with patch("app.decorators.retry.asyncio.sleep", new=AsyncMock()):
        limited = await limiter.is_limited("127.0.0.1", "parking_list", 5, 5)

    assert limited is False
    assert pipe.calls.count(("execute", {})) == 2  # 1 неудача + 1 успех


async def test_is_limited_retries_on_response_error():
    limiter, _, pipe = make_limiter(
        [0, 1, 1, 1],
        execute_side_effect=[ResponseError("boom")],
    )

    with patch("app.decorators.retry.asyncio.sleep", new=AsyncMock()):
        limited = await limiter.is_limited("127.0.0.1", "parking_list", 5, 5)

    assert limited is False
    assert pipe.calls.count(("execute", {})) == 2
