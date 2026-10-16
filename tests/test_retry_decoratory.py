from unittest.mock import AsyncMock, call, patch

import pytest

from app.decorators import retry


async def test_retry_success_after_failures():
    """Функция падает дважды, затем успешно возвращает результат."""
    calls = 0

    @retry(retries=3, delay=0, exceptions=(ValueError,))
    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("boom")
        return "ok"

    with patch("app.decorators.retry.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        result = await flaky()

    assert result == "ok"
    assert calls == 3  # 2 неудачи + 1 успех
    mock_sleep.assert_awaited()


async def test_retry_exhausts_and_raises_last_exception():
    """Функция всегда падает — после retries попыток пробрасывается последнее исключение."""
    calls = 0

    @retry(retries=3, delay=0, exceptions=(ValueError,))
    async def always_fails():
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    with (
        patch("app.decorators.retry.asyncio.sleep", new=AsyncMock()),
        pytest.raises(ValueError, match="boom"),
    ):
        await always_fails()

    assert calls == 3


async def test_retry_does_not_retry_on_unlisted_exception():
    """Исключение не из списка exceptions — ретрая нет, пробрасывается сразу."""
    calls = 0

    @retry(retries=3, delay=0, exceptions=(ValueError,))
    async def raises_type_error():
        nonlocal calls
        calls += 1
        raise TypeError("not retried")

    with (
        patch("app.decorators.retry.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        pytest.raises(TypeError),
    ):
        await raises_type_error()

    assert calls == 1
    mock_sleep.assert_not_awaited()


async def test_retry_applies_backoff_delay():
    """
    Проверка расчёта задержки с джиттером:
    интервал для uniform: (0, delay * backoff_factor ** (attempt - 1)).
    """
    calls = 0

    @retry(retries=3, delay=1, backoff_factor=2.0, exceptions=(ValueError,))
    async def flaky():
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    with (
        patch("app.decorators.retry.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        patch("app.decorators.retry.random.uniform", side_effect=lambda a, b: b) as mock_uniform,
        pytest.raises(ValueError),
    ):
        await flaky()

    # формула: попытка 1 -> 1 * 2**0 = 1.0; попытка 2 -> 1 * 2**1 = 2.0
    assert mock_uniform.call_args_list == [call(0, 1.0), call(0, 2.0)]
    # uniform возвращает верхнюю границу -> sleep получает 1.0 и 2.0
    assert mock_sleep.await_args_list == [call(1.0), call(2.0)]


async def test_retry_retries_one_means_no_retry():
    """retries=1 — повторных попыток нет, sleep не вызывается."""
    calls = 0

    @retry(retries=1, delay=0, exceptions=(ValueError,))
    async def flaky():
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    with (
        patch("app.decorators.retry.asyncio.sleep", new=AsyncMock()) as mock_sleep,
        pytest.raises(ValueError),
    ):
        await flaky()

    assert calls == 1
    mock_sleep.assert_not_awaited()
