# Архитектура проекта

> Документ сверен с кодом после Фазы 2.5 (2026-07-16). Описывает фактическое состояние.

## Стек

| Компонент | Технология |
|-----------|-----------|
| Бот | Python + aiogram 3 (long polling) |
| Админка | Python + FastAPI + Jinja2 + SQLAlchemy 2 (async) |
| БД | PostgreSQL (Docker) |
| ORM | SQLAlchemy 2 async (asyncpg) |
| Планировщик | APScheduler (AsyncIOScheduler, MemoryJobStore) |
| Контейнеры | Docker + docker-compose |
| Reverse proxy | Caddy (на сервере) |

## Порты

Оба порта слушают ТОЛЬКО на localhost (проброс `127.0.0.1:...` в docker-compose) — наружу не торчат, доступ снаружи только через Caddy (HTTPS).

| Сервис | Порт | Назначение |
|--------|------|-----------|
| Бот | — | Фоновый процесс, портов не слушает |
| Админка | 127.0.0.1:5000 | Caddy проксирует `andrew-bot-adminka.mak-o.ru` → localhost:5000 |
| PostgreSQL | 127.0.0.1:5433 | Только локально |

## Инициализация БД

Таблицы/enum-типы создаёт **только админка** (`init_db()` → `create_all` в её lifespan). Бот при старте НЕ делает `create_all`, а ждёт готовности БД (`wait_for_db`: `SELECT 1 FROM users`, ретрай до 60 сек). Это исключает гонку двух сервисов на первом деплое. Изменения схемы на проде — вручную через `docs/migrations/*.sql` (Alembic не используется).

## Структура проекта

```
TG_obuch2/
├── docker-compose.yml
├── .env                          # секреты (в git не коммитить)
├── shared/                       # общий код бота и админки
│   ├── config.py                 # env-переменные (fail-fast), DSN с quote_plus, TZ=Europe/Moscow
│   ├── database.py               # async-движок, async_session, Base, init_db
│   ├── models.py                 # ВСЕ SQLAlchemy-модели (единый файл)
│   ├── funnel.py                 # STAGE_ORDER + advance_stage (этап только вперёд)
│   └── notifier.py               # прямые HTTP-уведомления в Telegram из админки (httpx)
├── bot/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # точка входа: wait_for_db, прокси, Dispatcher, middlewares, mailing_loop
│       ├── keyboards.py          # все инлайн-клавиатуры
│       ├── states.py             # FSM-состояния (QuestionState, ObjectState)
│       ├── handlers/
│       │   ├── start.py          # /start, /menu, согласие (accept_all), интро, цель, воронка примеров, неизвестные команды
│       │   ├── menu.py           # главное меню, «Записаться», «О курсе», «Программа», «Примеры»
│       │   ├── course.py         # «Подробнее о курсе», тарифы, сравнение тарифов
│       │   ├── examples.py       # меню «Примеры работ»
│       │   ├── reviews.py        # меню «Отзывы» + воронковая цепочка отзывов
│       │   ├── faq.py            # ЧаВо
│       │   ├── question.py       # «Задать вопрос» + автопересылка любых сообщений в поддержку
│       │   ├── object.py         # анкета «Предложить свой объект» (FSM)
│       │   ├── support.py        # ответы админов из группы поддержки → пользователю (copy_message)
│       │   └── consent.py        # отзыв согласия (обезличивание журнала, удаление данных)
│       ├── middlewares/
│       │   ├── db.py             # сессия БД на каждый апдейт (data["session"])
│       │   └── consent.py        # блок без согласий (пускает только /start и accept_all), анти-спам экрана
│       └── services/
│           ├── cache.py          # кэш file_id по пути+mtime, upsert (ON CONFLICT)
│           ├── legal.py          # ссылки на юр-документы и бесплатные уроки
│           ├── app_settings.py   # get_setting / get_tariff_urls (ссылки GetCourse из настроек)
│           ├── support_service.py# ensure_thread (per-user Lock), deliver_to_support (copy_to), пересоздание закрытой темы
│           ├── delayed.py        # run_detached — отложенные цепочки без удержания сессии БД
│           └── mailing.py        # process_mailings (сбор получателей, RetryAfter, статусы, логи батчем)
├── admin/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI (lifespan → init_db), монтирование роутеров и static
│       ├── dependencies.py       # templates + jinja (msk, full_name, goal_ru, stage_ru), get_db, require_auth
│       ├── routers/
│       │   ├── auth.py           # логин (compare_digest, cookie samesite=lax), логаут
│       │   ├── dashboard.py      # статистика + воронка по STAGE_ORDER
│       │   ├── users.py          # список/поиск (имя/username/телефон/id)/карточка, пагинация
│       │   ├── mailings.py       # создание/повтор/отмена рассылок, счётчики доставки, пагинация
│       │   ├── objects.py        # список/карточка, назначение (datalist)/отклонение/возврат, выгрузка .txt
│       │   ├── legal.py          # загрузка/публичная выдача юр-документов
│       │   └── settings.py       # прокси, ссылки уроков/тарифов
│       ├── templates/            # base, login, dashboard, users, user_detail, mailings,
│       │   │                     # mailing_create, objects, object_detail, legal, settings
│       └── static/               # (стили инлайн в base.html; каталог смонтирован, но не используется)
├── files/
│   ├── images/                   # отзыв_анна.jpg, отзыв_владимир.jpg, сравнительнаятаблица.png
│   └── video/                    # видео_пример_1..3.mp4
└── docs/
    ├── TZ.md                     # исходное ТЗ
    ├── ARCHITECTURE.md           # этот файл
    ├── CODE_REVIEW.md            # ревью (5 проходов)
    ├── FIX_DESIGN.md             # проект исправлений Фазы 2.5
    └── migrations/               # SQL-миграции для прод-БД
```

## Модель данных (shared/models.py)

10 таблиц. Отличия от первичной схемы (по итогам Фазы 2.5) выделены.

- **users** — id, telegram_id (UNIQUE), username, first_name, last_name, phone, goal(enum), consent_offer, consent_personal_data, funnel_stage, support_thread_id, created_at, updated_at.
- **consent_log** — id, **user_id (FK, NULLABLE)**, consent_type(enum), **telegram_id (BIGINT)**, accepted, timestamp. При отзыве согласия записи обезличиваются (user_id→NULL, telegram_id заполняется), журнал сохраняется (152-ФЗ).
- **questions** — id, user_id, message_text, status, created_at.
- **objects** — id, user_id, **object_name (NULLABLE)**, address, description, photo_links, video_links, budget, status(enum: pending/accepted/assigned/rejected), assigned_to (FK NULL), admin_notes, **cancelled (BOOL)**, created_at, updated_at. Новые объекты приходят со статусом `accepted`; `cancelled=True` — пользователь прервал анкету (частичное сохранение).
- **mailings** — id, message_text, target_category(enum), scheduled_at (naive UTC), status(enum: pending/sending/sent/cancelled/error), created_at.
- **mailing_logs** — id, mailing_id, user_id, status(enum: sent/failed), error_message, sent_at.
- **legal_documents** — id, document_type(enum: offer/privacy_policy/personal_data_policy/free_lessons), file_path, file_name, uploaded_at, is_active.
- **analytics_events** — id, user_id, event_type, metadata(JSON), timestamp.
- **settings** — id, key(UNIQUE), value, updated_at. Ключи: `proxy_url`, `free_lessons_url`, `tariff_self_url`, `tariff_support_url`, `tariff_pro_url`.
- **cached_files** — id, file_path(UNIQUE), file_id, file_type, **file_mtime (FLOAT)**, created_at. Кэш инвалидируется при изменении mtime файла.

## Ключевые потоки

### Воронка продаж (бот)
```
/start → экран согласия (3 ссылки + «Принять» = accept_all: оба флага + 2 ConsentLog)
→ CONFIRM_TEXT «Кто мы» → «Далее» → «Какая у вас цель?» (3 кнопки, персональный ответ)
→ интро-текст → видео 5/20/20с → +30с «4 бесплатных урока» + «Посмотрел»
→ (кнопка ИЛИ таймер APScheduler 30 мин) → цепочка отзывов → «Подробнее о курсе»
→ О курсе → +15с программа → «Узнать тарифы» → 3 тарифа + таблица → «Выберите тариф» (GetCourse-ссылки)
```
Отложенные цепочки — через `run_detached` (не держат сессию БД на sleep'ах); `funnel_stage` двигается только вперёд (`advance_stage`).

### Согласие и доступ
Без обоих согласий `ConsentMiddleware` пропускает только `/start` и callback `accept_all`; на остальное показывает экран согласия (анти-спам 15 сек). Отзыв согласия: снятие назначений чужих объектов, обезличивание журнала, удаление темы поддержки и данных, затем снова экран согласия.

### Группа поддержки
```
Пользователь пишет что угодно боту (после согласий)
→ support_service.deliver_to_support: ensure_thread (создаёт тему, per-user Lock) → message.copy_to(тема)
→ при закрытой/удалённой теме — пересоздание и повтор
Админ отвечает в теме → support.py: copy_message → пользователю (любой тип контента)
```

### Уведомления о назначении объекта
Единственный механизм — `shared/notifier.py`, вызывается из админки при назначении через FastAPI `BackgroundTasks` (страница не висит на HTTP к Telegram). Поля экранируются `html.escape`. (Старые `check_new_orders` и `services/notification.py` удалены.)

### Рассылки
`mailing_loop` в боте раз в минуту зовёт `process_mailings`: выбирает готовые (scheduled_at ≤ now в UTC), помечает `sending`, собирает получателей заранее, шлёт с паузой 0.05с и одним повтором при `TelegramRetryAfter`, пишет логи батчем, ставит статус `sent`/`error`. При старте бота зависшие `sending` возвращаются в `pending`. Время в админке вводится/показывается в МСК (`TZ`, фильтр `msk`), хранится как naive UTC.

## Docker (docker-compose.yml, схема)
```yaml
services:
  db:        # postgres, порт "127.0.0.1:5433:5432", volume pgdata, healthcheck
  admin:     # build ./admin, "127.0.0.1:5000:5000", volume uploads:/app/uploads, depends_on db(healthy)
  bot:       # build ./bot, depends_on admin(started)+db(healthy), restart: always
volumes: [pgdata, uploads]
```

## Caddy
```
andrew-bot-adminka.mak-o.ru { reverse_proxy localhost:5000 }
```

## Безопасность
- Порты БД и админки — только localhost; наружу через Caddy (HTTPS).
- Пароль админки — `secrets.compare_digest`, задержка 1с при ошибке, cookie httponly+samesite=lax.
- DSN экранирует логин/пароль (`quote_plus`) — спецсимволы в пароле безопасны.
- Токен бота, CHAT_ID, пароли — только в `.env` (fail-fast при отсутствии обязательных).
- Загрузка юр-документов: whitelist расширений, uuid-имя на диске, лимит 20 МБ, PDF отдаётся `inline`.
- FSM — MemoryStorage (осознанно): сценарии короткие, `/start`/`/menu` чистят state. Таймер отзывов (MemoryJobStore) не переживает рестарт — допущение.
```
