# Parking App 🚗

Асинхронный REST API для управления парковкой: учёт заездов и выездов автомобилей, история по номеру и автоматический расчёт стоимости парковки по тарифной сетке.

## ✨ Возможности

- **Парковка машины** (`POST /v1/cars/park/`) — регистрация заезда, защита от повторной парковки одной машины;
- **Выезд с парковки** (`PATCH /v1/cars/unpark/`) — фиксация выезда с расчётом времени и стоимости;
- **Список всех машин** и **история по номеру** — каждая запись сопровождается временем парковки и ценой;
- **Курсорная пагинация** — список и история разбиваются на страницы (`limit` до 50), навигация по курсору `(id, created_at)` без дубликатов и пропусков; при одинаковых `created_at` порядок стабилизируется по `id` (tie-break);
- **Динамическое ценообразование** — три тарифные зоны (короткая / средняя / длительная стоянка) через паттерн *Strategy*;
- **Защита от гонок** — строковые блокировки `SELECT ... FOR UPDATE` + частичный уникальный индекс в PostgreSQL гарантируют единственную активную парковку на номер даже при параллельных запросах;
- **Единый формат ошибок** — `{"error": "...", "message": "..."}` с понятными HTTP-кодами (400/404/409); ошибки валидации параметров и тела запроса — стандартный формат FastAPI (422);
- **Валидация госномера** — при парковке поле `number` проверяется регулярным выражением: 2 буквы (латиница или кириллица) + 2–4 цифры + обязательная буква в конце (итого 6–8 символов); некорректный формат отклоняется с `422`;
- **Структурированные JSON-логи** — каждый запрос логируется (loguru) с уникальным `request_id`, методом, путём, статусом и временем обработки; ответу добавляется заголовок `X-Request-ID`;
- **Мониторинг** — метрики Prometheus по `/health/metrics` (RPS, латентность p50/p90/p99, активные запросы) и готовый дашборд Grafana;
- **Тесты** — покрытие ~95% (юнит + интеграционные + конкурентные сценарии + пагинация + валидация схем).

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
| Логирование | loguru |
| Пакетный менеджер | uv |
| Качество кода | ruff, mypy |
| Тесты | pytest, pytest-asyncio, pytest-cov, httpx |
| Мониторинг | Prometheus, Grafana, prometheus-client |

## 📁 Структура проекта

```
app/
├── main.py                      # Точка входа FastAPI
├── config.py                    # Настройки (pydantic-settings)
├── uow.py                       # Паттерн Unit of Work
├── middlewares/
│   └── log.py                   # HTTP-логирование (loguru) + request_id
├── core/
│   └── database.py              # Движки, фабрики сессий, naming convention
├── domains/
│   ├── dependencies.py          # FastAPI DI (Annotated), в т.ч. курсорная пагинация
│   └── v1/cars/
│       ├── cars.py              # Роутер (эндпоинты /v1/cars/...)
│       ├── schemas.py           # Pydantic-схемы (вход/выход + курсоры пагинации)
│       ├── service.py           # Бизнес-логика, расчёт цены и агрегация страниц
│       └── repository.py        # Доступ к данным (SQL c курсорной выборкой)
├── errors/                      # Иерархия исключений + хендлеры
├── models/                      # SQLAlchemy-модели и миксины
├── migrations/                  # Alembic-миграции
└── park_price/                  # Тарифные стратегии ценообразования
tests/                           # Юнит-, интеграционные, router-, конкурентные тесты и тесты схем
prometheus/
│   └── prometheus.yml            # Конфигурация Prometheus: scrape-таргеты, интервалы
grafana/
│   └── grafana_dashboard.json    # Дашборд Grafana (импорт через UI)
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
docker compose -f compose.dev.yaml up -d

# 4. Применить миграции
uv run alembic upgrade head

# 5. Запустить сервер
uv run uvicorn app.main:app --reload
```

Интерактивная документация API — <http://localhost:8000/docs> (Swagger UI).

**Мониторинг (опционально):** запуск Prometheus и Grafana описан в разделе **📊 Мониторинг (Prometheus + Grafana)** ниже.

## 🔌 API

| Метод | Путь | Описание | Ответы |
|---|---|---|---|
| `GET` | `/v1/cars/` | Все машины с временем и ценой (курсорная пагинация) | 200, 422 |
| `GET` | `/v1/cars/{car_number}` | История заездов/выездов по номеру (курсорная пагинация) | 200, 422 |
| `POST` | `/v1/cars/park/` | Припарковать машину | 201, 409, 422 |
| `PATCH` | `/v1/cars/unpark/` | Выезд с парковки (цена + время) | 200, 400, 404 |

### 📄 Курсорная пагинация

Оба GET-эндпоинта принимают query-параметры:

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `limit` | int | `5` | Размер страницы, диапазон 1–50 |
| `cursor_id` | UUID | — | `last_id` из `next_cursor` предыдущей страницы |
| `created_at` | datetime | — | `last_created_at` из `next_cursor` предыдущей страницы |

Параметры `cursor_id` и `created_at` передаются **только парой** — при передаче лишь одного из них API вернёт `422`. Порядок записей — `created_at DESC, id DESC`: если несколько машин припаркованы в одну и ту же секунду, стабильность границ страниц обеспечивает tie-break по `id`.

Пример ответа `GET /v1/cars/?limit=1`:

```json
{
  "parking_and_price_data": [
    {
      "parking_data": {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "mark": "Toyota",
        "model": "Corolla",
        "number": "a123BC",
        "color": "red",
        "status": "parked",
        "created_at": "2026-10-03T12:00:00Z",
        "updated_at": "2026-10-03T12:00:00Z"
      },
      "price_time_data": {
        "park_time": 0.0,
        "price": 100.0
      }
    }
  ],
  "has_more": true,
  "next_cursor": {
    "last_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "last_created_at": "2026-10-03T12:00:00Z"
  }
}
```

Следующая страница запрашивается по полученному курсору:

```text
GET /v1/cars/?limit=1&cursor_id=3fa85f64-5717-4562-b3fc-2c963f66afa6&created_at=2026-10-03T12:00:00Z
```

Пока в базе есть ещё записи — `has_more: true` и `next_cursor` заполнен; на последней странице `has_more: false`, а `next_cursor: null`. Если история по номеру пуста или номер не найден — возвращается `200` с пустым `parking_and_price_data`.

### Пример запроса парковки

```json
POST /v1/cars/park/
{
  "mark": "Toyota",
  "model": "Corolla",
  "number": "ab123c",
  "color": "red"
}
```

Формат поля `number` в `CarParkSchema` проверяется регулярным выражением: **2 буквы** (латиница `A–Z/a–z` или кириллица `А–Я/а–я/Ё/ё`), затем **2–4 цифры**, далее ноль или более букв и **обязательная буква в конце** (суммарная длина 6–8 символов). Смешивать алфавиты нельзя. Примеры валидных номеров: `ал756р`, `AB123C`, `ам456хх`.

### Пример ответа выезда

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
    "park_time": 90.0,
    "price": 840.0
  }
}
```

### Формат ошибок

Бизнес-ошибки возвращаются в едином формате:

```json
{
  "error": "car_already_parked",
  "message": "Машина уже припаркована."
}
```

Ошибки валидации query-параметров (например, курсор передан не парой) и тела запроса (например, некорректный формат госномера) — стандартный ответ FastAPI `422` с полем `detail`.

## 💰 Тарифы

Стоимость рассчитывается от времени парковки в минутах (разница `updated_at − created_at`):

| Зона | Длительность | Формула |
|---|---|---|
| `short` | до 60 мин | `100 + 10 × мин` |
| `mid` | 60–119 мин | `120 + 8 × мин` |
| `long` | от 120 мин | `200 + 7 × мин` |

Границы: ровно 60 мин → зона `mid`, ровно 120 мин → зона `long` (граничные случаи покрыты тестами).

Логика выбора зоны — [`app/park_price/get_price.py`](app/park_price/get_price.py), формулы — [`app/park_price/pricing_strategies.py`](app/park_price/pricing_strategies.py).

## 📊 Мониторинг (Prometheus + Grafana)

Приложение экспонирует метрики в формате Prometheus по адресу **`GET /health/metrics`** ([`app/domains/health.py`](app/domains/health.py:7)). Метрики собираются автоматически middleware [`app/middlewares/metrics_middleware.py`](app/middlewares/metrics_middleware.py) и обновляются в реальном времени.

### Собираемые метрики

- `http_requests_total` — общее количество HTTP-запросов (Counter) с лейблами `method`, `endpoint`, `status_code`;
- `http_request_duration_seconds` — время выполнения HTTP-запросов (Histogram) с лейблами `method`, `endpoint`, `status_code` и бакетами [0.1, 0.3, 0.5, 1.0, 2.0, 5.0] секунд;
- `active_requests` — количество активных (in-progress) HTTP-запросов в данный момент (Gauge) с лейблами `method`, `endpoint`.

### Запуск

Prometheus и Grafana поднимаются через [`compose.prod.yaml`](compose.prod.yaml) — сервисы находятся в одной сети `parking_network` с приложением:

```bash
# создать prod-окружение, если ещё не создано
cp .env.example .env.prod

# поднять Prometheus и Grafana
docker compose -f compose.prod.yaml up -d prometheus grafana
```

- **Prometheus** — UI на <http://localhost:9090>: сбор метрик каждые 15 секунд (job `fastapi-app`, таргет `parking:8000`, конфиг [`prometheus/prometheus.yml`](prometheus/prometheus.yml));
- **Grafana** — UI на <http://localhost:3000>, вход `admin` / пароль из `GF_SECURITY_ADMIN_PASSWORD` (передаётся через `env_file: .env.prod`, см. [`compose.prod.yaml`](compose.prod.yaml); пароль по умолчанию обязательно сменить!).

### Подключение Grafana к Prometheus и импорт дашборда

1. **Data sources** → **Add data source** → **Prometheus**;
2. В поле *Prometheus server URL* указать `http://prometheus:9090` (адрес внутри сети Docker);
3. Нажать **Save & Test**;
4. **Dashboards** → **Import** → загрузить файл [`grafana/grafana_dashboard.json`](grafana/grafana_dashboard.json) → **Load** → **Import**.

### Панели дашборда

| Панель | Запрос PromQL |
|---|---|
| RPS (Requests Per Second) | `rate(http_requests_total[1m])` |
| Total Requests (Last 5m) | `sum by (method, endpoint, status_code)(increase(http_requests_total[5m]))` |
| Latency Percentiles (p50, p90, p99) | `histogram_quantile` по `http_request_duration_seconds_bucket` |
| Active Requests (In-Progress) | `active_requests` |
| Top Slow Endpoints (p99, last 5m) | `histogram_quantile(0.99, ...)` по `http_request_duration_seconds_bucket` |

## 📜 Логирование

Структурированное логирование на базе [loguru](https://github.com/Delgan/loguru): настройка выполняется в `lifespan` при старте приложения ([`app/main.py`](app/main.py)), реализация — [`app/middlewares/log.py`](app/middlewares/log.py).

- каждый HTTP-запрос фиксируется одной JSON-записью: `request_id`, метод, путь, `status_code`, `process_time_ms`, IP клиента и `user_agent`;
- каждому запросу присваивается уникальный `request_id` (UUID), который возвращается в заголовке ответа **`X-Request-ID`** и через `ContextVar` подмешивается во все логи в рамках запроса — по нему можно проследить весь жизненный цикл запроса;
- уровень записи зависит от статуса ответа: `INFO` (< 400), `WARNING` (4xx), `ERROR` (5xx); необработанные исключения дополнительно логируются со стектрейсом (`logger.exception`);
- логи пишутся асинхронно (`enqueue=True`) в файл `logs/logs.log` в формате JSON (`serialize=True`): ротация при 10 МБ, архивация `zip`, хранение 30 дней, кодировка UTF-8;
- служебные пути `/health/metrics` и `/favicon.ico` не логируются (скрейпы Prometheus не засоряют лог);
- `diagnose=False` предотвращает утечку значений переменных в стектрейсах.

## 🧪 Тестирование

```bash
# 1. Поднять тестовую БД
docker compose -f compose.test.yaml up -d

# 2. Настроить тестовое окружение
cp .env.example.test .env.test

# 3. Запустить тесты (покрытие ~95%, отчёт в htmlcov/)
uv run pytest
```

Тесты используют реальный PostgreSQL (`NullPool`-сессии, отдельное соединение на каждый тест) и покрывают:

- **конкурентные сценарии** — параллельные `park`/`unpark` одного номера из нескольких транзакций: гонка разрешается через `FOR UPDATE` и частичный уникальный индекс, в базе остаётся ровно одна `parked`-запись;
- **курсорную пагинацию** — `has_more`, `next_cursor`, переходы между страницами без дубликатов и потерь, tie-break по `id` при равных `created_at`, фильтрация по номеру;
- **валидацию курсора** — `cursor_id` и `created_at` только парой (`422`), границы `limit` (1–50);
- **границы тарифов** — ровно 60 мин → `mid`, ровно 120 мин → `long`;
- **валидацию Pydantic-схем** (`tests/test_schemas.py`) — длины полей `mark`/`model`/`number`, границы `limit` (1–50), парность курсора и формат госномера по регулярному выражению: корректные номера (латиница и кириллица) проходят, а смешение алфавитов, отсутствие букв или неверное количество цифр отклоняются с `422`;
- **бизнес-правила** — повторная парковка уже стоящей машины (`409`), выезд неприпаркованной (`400`), выезд несуществующей (`404`), повторная парковка после выезда (частичный индекс).

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
| `GF_SECURITY_ADMIN_USER` | `admin` | Логин администратора Grafana |
| `GF_SECURITY_ADMIN_PASSWORD` | `admin` | Пароль администратора Grafana (обязательно сменить в проде!) |

Переменные `GF_*` используются сервисом Grafana в [`compose.prod.yaml`](compose.prod.yaml) (через `env_file: .env.prod`). Тестовая среда использует те же переменные из `.env.test` (порт `16432`, база `test_db`, `ENVIRONMENT=TEST`).

## 🧹 Качество кода

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app