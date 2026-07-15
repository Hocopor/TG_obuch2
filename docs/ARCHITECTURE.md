# Архитектура проекта

## Стек

| Компонент | Технология |
|-----------|-----------|
| Бот | Python 3.12 + aiogram 3 |
| Админка | Python 3.12 + FastAPI + Jinja2 + SQLAlchemy |
| БД | PostgreSQL 16 (Docker) |
| ORM | SQLAlchemy 2.0 (async, asyncpg) |
| Контейнеры | Docker + docker-compose |
| Reverse proxy | Caddy (уже на сервере) |

## Порты

| Сервис | Порт | Назначение |
|--------|------|-----------|
| Бот | — | Фоновый процесс, порт не слушает |
| Админка | 5000 | Внутренний, Caddy проксирует |
| PostgreSQL | 5433 | Внутренний (из контейнера наружу) |

## Структура проекта

```
tg_bot/
├── docker-compose.yml
├── .env
├── bot/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py              # Точка входа бота
│       ├── config.py            # Настройки из .env
│       ├── database.py          # Подключение к БД
│       ├── models.py            # SQLAlchemy модели
│       ├── handlers/
│       │   ├── __init__.py
│       │   ├── start.py         # /start, приветствие, согласия
│       │   ├── menu.py          # Главное меню
│       │   ├── course.py        # О курсе, программа, тарифы
│       │   ├── examples.py      # Примеры работ
│       │   ├── reviews.py       # Отзывы
│       │   ├── faq.py           # Частые вопросы
│       │   ├── question.py      # Задать вопрос → группа поддержки
│       │   ├── object.py        # Предложить свой объект
│       │   ├── support.py       # Обработка сообщений из группы поддержки
│       │   └── consent.py       # Отзыв согласия
│       ├── middlewares/
│       │   ├── __init__.py
│       │   ├── db.py            # Сессия БД на каждый апдейт
│       │   └── anti_spam.py     # Антиспам (по необходимости)
│       ├── services/
│       │   ├── __init__.py
│       │   ├── user.py          # CRUD пользователей
│       │   ├── support.py       # Работа с группой поддержки
│       │   ├── mailing.py       # Логика рассылок
│       │   └── legal.py         # Юр-документы
│       ├── states.py            # FSM-состояния
│       └── keyboards.py         # Все клавиатуры
├── admin/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI приложение
│       ├── config.py
│       ├── database.py
│       ├── models.py            # Те же модели (общая БД)
│       ├── dependencies.py      # Зависимости (сессия БД, авторизация)
│       ├── auth.py              # Авторизация админа
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── dashboard.py     # Дашборд / аналитика
│       │   ├── users.py         # Список / поиск / карточка пользователя
│       │   ├── mailings.py      # Рассылки
│       │   ├── objects.py       # Объекты
│       │   ├── legal.py         # Юр-документы
│       │   └── auth.py          # Логин/логаут
│       ├── templates/           # Jinja2 шаблоны
│       │   ├── base.html
│       │   ├── login.html
│       │   ├── dashboard.html
│       │   ├── users/
│       │   ├── mailings/
│       │   ├── objects/
│       │   └── legal/
│       └── static/              # CSS, JS
├── shared/
│   ├── __init__.py
│   ├── config.py                # Общие настройки
│   ├── database.py              # Движок БД (общий)
│   └── models.py                # Единый файл моделей
├── files/
│   ├── images/                  # Тестовые изображения
│   └── video/                   # Тестовые видео
└── docs/
    ├── TZ.md
    └── ARCHITECTURE.md
```

## Модель данных

### users
Основная таблица пользователей.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| telegram_id | BIGINT UNIQUE | Telegram user ID |
| username | VARCHAR(255) | @username |
| first_name | VARCHAR(255) | Имя |
| last_name | VARCHAR(255) | Фамилия |
| phone | VARCHAR(50) | Телефон (если собирается) |
| goal | ENUM | own_objects / earn_money / exploring_ai |
| consent_offer | BOOLEAN | Принята ли оферта |
| consent_personal_data | BOOLEAN | Принята ли политика ПДн |
| funnel_stage | VARCHAR(50) | Текущий этап воронки |
| support_thread_id | INTEGER | ID темы в группе поддержки |
| created_at | TIMESTAMP | Регистрация |
| updated_at | TIMESTAMP | Последнее обновление |

### consent_log
Журнал согласий (для юридической защиты).

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| user_id | FK → users | |
| consent_type | ENUM | offer / personal_data |
| accepted | BOOLEAN | |
| timestamp | TIMESTAMP | |

### questions
Вопросы пользователей (через кнопку "Задать вопрос" и обычные сообщения).

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| user_id | FK → users | |
| message_text | TEXT | Текст вопроса |
| status | ENUM | pending / answered / closed |
| created_at | TIMESTAMP | |

### objects
Предложенные объекты недвижимости.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| user_id | FK → users | |
| object_name | VARCHAR(500) | Название |
| address | TEXT | Адрес |
| description | TEXT | Что хотят видеть |
| photo_links | TEXT | Ссылки на фото |
| video_links | TEXT | Ссылки на видео |
| budget | VARCHAR(255) | Бюджет |
| status | ENUM | pending / accepted / assigned / rejected |
| assigned_to | FK → users NULL | Кому назначен |
| admin_notes | TEXT | Заметки админа |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### mailings
Рассылки.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| message_text | TEXT | Текст рассылки |
| target_category | ENUM | all / own_objects / earn_money / exploring_ai |
| scheduled_at | TIMESTAMP NULL | Когда отправить (NULL = сейчас) |
| status | ENUM | pending / sending / sent / cancelled / error |
| created_at | TIMESTAMP | |

### mailing_logs
Логи отправки рассылок.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| mailing_id | FK → mailings | |
| user_id | FK → users | |
| status | ENUM | sent / failed |
| error_message | TEXT NULL | |
| sent_at | TIMESTAMP | |

### legal_documents
Юридические документы (загружаются через админку).

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| document_type | ENUM | offer / privacy_policy / personal_data_policy |
| file_path | TEXT | Путь к файлу на диске |
| file_name | VARCHAR(255) | Оригинальное имя |
| uploaded_at | TIMESTAMP | |
| is_active | BOOLEAN | Активен ли документ |

### analytics_events
События аналитики воронки.

| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| user_id | FK → users | |
| event_type | VARCHAR(50) | Тип события |
| metadata | JSONB | Доп. данные |
| timestamp | TIMESTAMP | |

## Ключевые потоки

### Воронка продаж (бот)
```
/start → Приветствие → Оферта (принять) → ПДн (принять)
→ "Кто мы" → "Какая цель" (выбор) → Видео-примеры
→ Бесплатные уроки → "Посмотрел" (или 30 мин)
→ Отзывы → "Подробнее о курсе" → Программа
→ Тарифы → Выбор тарифа (внешняя ссылка на GetCourse)
```

### Группа поддержки
```
Пользователь пишет сообщение боту (после согласий)
→ Бот создаёт тему в группе (если ещё нет)
→ Пересылает сообщение в тему
Админ отвечает в тему
→ Бот ловит ответ (handler на сообщения из группы)
→ Пересылает пользователю
```

### Админка — навигация
```
/login → Авторизация (пароль)
→ Дашборд (аналитика: сколько пользователей, воронка, конверсия)
→ Пользователи (список, поиск, карточка)
→ Рассылки (создание, планирование, история)
→ Объекты (список, назначение/отклонение)
→ Юр-документы (загрузка, активация)
```

## Docker

### docker-compose.yml (схема)
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: tg_bot
      POSTGRES_USER: tg_bot
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5433:5432"

  bot:
    build: ./bot
    env_file: .env
    depends_on:
      - db
    restart: always

  admin:
    build: ./admin
    env_file: .env
    depends_on:
      - db
    ports:
      - "5000:5000"
    restart: always

volumes:
  pgdata:
```

## Caddy (конфиг для добавления)
```
andrew-bot-adminka.mak-o.ru {
    reverse_proxy localhost:5000
}
```

## Безопасность и изоляция
- Каждый сервис в своём Docker-контейнере
- БД доступна только изнутри Docker-сети (порт 5433 не expose наружу в продакшене)
- Админка за авторизацией (пароль в .env)
- Юр-документы хранятся на диске, отдаются по защищённой ссылке
- Telegram-токен и пароль БД — только в .env, не коммитятся
