# PaceReader

API ИИ‑сервиса: принимает текст или файл, а затем с помощью ИИ‑агента (с подключаемыми tools) превращает его в короткую структурированную версию и может показывать результат по одному слову через SSE.

## Что умеет
- Обрабатывает текст в два шага (ИИ‑агент + инструменты):
  - Tool: анонимизация (маскирование чувствительных данных перед отправкой в LLM).
  - Агент: “умное” сокращение и структурирование; в режиме `auto` сам выбирает нужный объём сокращения.
- LLM:
  - Perplexity - прямой запрос для анонимизация.
  - GigaChat - через function calling для суммаризации.
- Авторизация (JWT access/refresh)
- Эндпоинты для:
  - Сокращения текста из файла или из строки.
  - Показ текста по словам (SSE streaming), чтобы регулировать скорость чтения и удерживать внимание.

## Стек
- Python 3.11
- FastAPI (REST + SSE)
- PostgreSQL, SQLAlchemy, Alembic (миграции)
- Docker / Docker Compose
- LLM: Perplexity, GigaChat (`app/text/*_client.py`)

## Запуск через Docker
1) Создай `.env` и заполни его:
```bash
cp .env.example .env
```

2) Собери образы:
```bash
make docker-build
```

3) Примени миграции:
```bash
make docker-migrate
```

4) Запусти приложение:
```bash
make docker-up
```

Остановить:
```bash
make docker-down
```

## Запуск без Docker

1) Создай `.env` и заполни его:
```bash
cp .env.example .env
```

2) Создай `.venv` и установи зависимости:
```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

3) Запусти приложение:
```bash
make run
```

## Структура
- `app/main.py` — точка входа FastAPI
- `app/api/` — роуты: `auth.py`, `user.py`, `text.py`
- `app/auth/` — логика входа пользователя и JWT access/refresh
- `app/text/` — логика обработки/суммаризации текста
  - `app/text/tools/` — инструменты (анонимизация и сокращение)
  - `app/text/agents/` — ИИ‑агент
- `app/user/` — логика регистрации пользователя
- `alembic_migrations/` — миграции БД
- `uploads/` — загруженные файлы
