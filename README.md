# Parking App 🚗

Асинхронный REST API для управления парковкой: учёт заездов и выездов автомобилей, история по номеру и автоматический расчёт стоимости парковки по тарифной сетке.

## ✨ Возможности

- **Парковка машины** (`POST /v1/cars/park/`) — регистрация заезда, защита от повторной парковки одной машины;
- **Выезд с парковки** (`PATCH /v1/cars/unpark/`) — фиксация выезда с расчётом времени и стоимости;
- **Список всех машин** и **история по номеру** — каждая запись сопровождается временем парковки и ценой;
- **Динамическое ценообразование** — три тарифные зоны (короткая / средняя / длительная стоянка) через паттерн *Strategy*;
- **Защита от гонок** — строковые блокировки `SELECT ... FOR UPDATE` + частичный уникальный индекс в PostgreSQL гарантируют единственную активную парковку на номер даже при параллельных запросах;
- **Единый формат ошибок** — `{"error": "...", "message": "..."}` с понятными HTTP-кодами (400/404/409);
- **Тесты** — покрытие ~98% (юнит + интеграционные + конкурентные сценарии).

## 🛠 Технологический стек

| Слой | Технология |
|---|---|
| Язык | Python 3.12 |
| Веб-фреймворк | FastAPI |
| ORM | SQLAlchemy 2.x (async) |
| Драйвер БД | asyncpg |
| Миграции | Alembic |
| БД | PostgreSQL 17 |
| Валидация | Pydantic v2 |
| Пакетный менеджер | uv |
| Качество кода | ruff, mypy |
| Тесты | pytest, pytest-asyncio, pytest-cov, httpx |

## 📁 Структура проекта

```
app/
├── main.py                      # Точка входа FastAPI
├── config.py                    # Настройки (pydantic-settings)
├── uow.py                       # Паттерн Unit of Work
├── core/
│   └── database.py              # Движки, фабрики сессий, naming convention
├── domains/
│   ├── dependencies.py          # FastAPI DI (Annotated)
│   └── v1/cars/
│       ├── cars.py              # Роутер (эндпоинты /v1/cars/...)
│       ├── schemas.py           # Pydantic-схемы (вход/выход)
│       ├── service.py           # Бизнес-логика и расчёт цены
│       └── repository.py        # Доступ к данным
├── errors/                      # Иерархия исключений + хендлеры
├── models/                      # SQLAlchemy-модели и миксины
├── migrations/                  # Alembic-миграции
└── park_price/                  # Тарифные стратегии ценообразования
tests/                           # Юнит-, интеграционные и router-тесты
```

## 🚀 Быстрый старт

### Требования

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker (для локальной БД)

### Установка и запуск

```bash
# 1. Установить зависимости
uv sync

# 2. Настроить окружение (локальный конфиг)
cp .env.example .env.local

# 3. Поднять PostgreSQL
docker compose up -d

# 4. Применить миграции
uv run alembic upgrade head

# 5. Запустить сервер
uv run uvicorn app.main:app --reload
```

Интерактивная документация API — <http://localhost:8000/docs> (Swagger UI).

## 🔌 API

| Метод | Путь | Описание | Ответы |
|---|---|---|---|
| `GET` | `/v1/cars/` | Все машины с временем и ценой | 200 |
| `GET` | `/v1/cars/{car_number}` | История заездов/выездов по номеру | 200 |
| `POST` | `/v1/cars/park/` | Припарковать машину | 201, 409 |
| `PATCH` | `/v1/cars/unpark/` | Выезд с парковки (цена + время) | 200, 400, 404 |

Пример запроса парковки:

```json
POST /v1/cars/park/
{
  "mark": "Toyota",
  "model": "Corolla",
  "number": "a123BC",
  "color": "red"
}
```

Пример ответа выезда:

```json
PATCH /v1/cars/unpark/
{
  "number": "a123BC"
}
```

```json
{
  "parking_data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "mark": "Toyota",
    "model": "Corolla",
    "number": "a123BC",
    "color": "red",
    "status": "unparked",
    "created_at": "2026-10-03T12:00:00Z",
    "updated_at": "2026-10-03T13:30:00Z"
  },
  "price_time_data": {
    "park_time": "Время парковки: 90.0 мин.",
    "price": "Стоимость: 840.0 руб."
  }
}
```

Формат ошибки:

```json
{
  "error": "car_already_parked",
  "message": "Машина уже припаркована."
}
```

## 💰 Тарифы

Стоимость рассчитывается от времени парковки в минутах (разница `updated_at − created_at`):

| Зона | Длительность | Формула |
|---|---|---|
| `short` | до 60 мин | `100 + 10 × мин` |
| `mid` | 60–119 мин | `120 + 8 × мин` |
| `long` | от 120 мин | `200 + 7 × мин` |

Логика выбора зоны — [`app/park_price/get_price.py`](app/park_price/get_price.py), формулы — [`app/park_price/pricing_strategies.py`](app/park_price/pricing_strategies.py).

## 🧪 Тестирование

```bash
# 1. Поднять тестовую БД
docker compose -f compose.test.yaml up -d

# 2. Настроить тестовое окружение
cp .env.example.test .env.test

# 3. Запустить тесты (покрытие ~98%, отчёт в htmlcov/)
uv run pytest
```

Тесты используют реальный PostgreSQL (`NullPool`-сессии, отдельное соединение на каждый тест) и включают сценарий конкурентного выезда, проверяющий корректность `FOR UPDATE`.

## 🔒 Конкуренция и целостность

- Параллельные `park` одного номера блокируются **частичным уникальным индексом** `uq_cars_number_parked` (уникальность только для строк со статусом `parked` — история не ограничивается);
- Последовательность «проверил статус → изменил» защищена `SELECT ... FOR UPDATE` в рамках транзакции Unit of Work;
- `UnitOfWork` автоматически делает `commit` при успехе и `rollback` при ошибке.

## ⚙️ Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---|---|
| `ENVIRONMENT` | `LOCAL` | Окружение: `LOCAL` / `TEST` / `DEV` / `PROD` |
| `DB_DRIVER` | `postgresql+asyncpg` | Драйвер БД |
| `POSTGRES_USER` | `postgres` | Пользователь БД |
| `POSTGRES_PASSWORD` | `postgres` | Пароль БД |
| `DB_HOST` | `localhost` | Хост БД |
| `DB_PORT` | `6432` | Порт БД (локальный compose: `6432 → 5432`) |
| `POSTGRES_DB` | `parking` | Имя БД |

Тестовая среда использует те же переменные из `.env.test` (порт `16432`, база `test_db`, `ENVIRONMENT=TEST`).

## 🧹 Качество кода

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app