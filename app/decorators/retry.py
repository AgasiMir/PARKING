import asyncio
import random
from collections.abc import Callable
from functools import wraps
from typing import Any

from app.middlewares.log import logger


def retry(
    *,
    retries: int = 3,
    delay: float = 3,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    backoff_factor: float = 2,
):
    """
    Декоратор для повторного выполнения асинхронной функции при возникновении указанных исключений.

    Args:
        retries: Количество повторных попыток (включая первую)
        delay: Базовая задержка между попытками в секундах
        exceptions: Кортеж исключений, которые должны вызывать повторную попытку
        backoff_factor: Множитель для увеличения задержки с каждой попыткой
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as err:
                    last_exception = err
                    logger.warning(
                        f"Попытка {attempt}/{retries} не удалась для {func.__name__}: {err}"
                    )
                    if attempt < retries:
                        current_delay = delay * (backoff_factor ** (attempt - 1))
                        current_delay = random.uniform(0, current_delay)
                        await asyncio.sleep(current_delay)

            if last_exception:
                raise last_exception

        return wrapper

    return decorator
