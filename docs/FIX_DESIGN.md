# Проект исправлений по ревью (docs/CODE_REVIEW.md)

Дата: 2026-07-16. Спроектировано оркестратором, реализуется сабагентами по блокам.
Решения заказчика: **14 уроков** (не 13 — в тарифе «Самостоятельный» писать «14 уроков»);
**одна галочка согласия** вместо двух; журнал согласий **хранить** после отзыва;
меню «Отзывы» — **строго по ТЗ** (2 отзыва); телефон в поиске **оставить, сбор не делать**;
бесплатные уроки — **одна внешняя ссылка** (поле в настройках админки).

Нумерация багов (№1–14, Т1–Т21 и пр.) — по `docs/CODE_REVIEW.md`.

---

## Блок 0 — Ручные шаги (делает пользователь, не сабагенты)

1. Отозвать токен бота через @BotFather (`/revoke`), новый токен — только в локальный `.env`.
2. Вычистить `.env` из git-истории (`git rm --cached .env`, затем `git filter-repo --path .env --invert-paths`, если репо куда-то пушится).
3. Сменить `ADMIN_PASSWORD` и `DB_PASSWORD` на стойкие (после фикса B7 спецсимволы в пароле БД безопасны).
4. `git rm --cached` для `__pycache__`, `*.pyc`, `.mov` (уже в .gitignore, но остались в индексе).
5. В BotFather прописать description («What can this bot do?») — текст `WELCOME_TEXT` из ТЗ (Т7).
6. При деплое: выполнить `docs/migrations/2026-07-16_fixes.sql` на проде; перенести уже загруженные файлы из `/uploads` контейнера admin в volume (`docker cp` или пере-загрузка документов через админку).

---

## Блок A — Безопасность и инфраструктура

**A1. Порты только на localhost** (`docker-compose.yml`): `"127.0.0.1:5433:5432"`, `"127.0.0.1:5000:5000"`. Caddy на той же машине — localhost достаточно.

**A2. `create_all` делает только admin** (гонка при первом деплое):
- `bot/app/main.py`: убрать `create_all`; вместо него retry-loop при старте: `SELECT 1 FROM users LIMIT 1` раз в 2 сек до успеха (макс 60 сек, потом падение с понятной ошибкой «БД не инициализирована»).
- `docker-compose.yml`: `bot` → `depends_on: admin` (service_started) + db healthy.

**A3. DSN с экранированием** (`shared/config.py`): `urllib.parse.quote_plus(DB_PASSWORD)` (и юзера) при сборке URL.

**A4. Fail-fast конфиг** (`shared/config.py`): при импорте проверять `TELEGRAM_BOT_TOKEN`, `CHAT_ID`; в боте — `ADMINKA_URL`. Пусто → `raise RuntimeError` с именем переменной.

**A5. `.gitignore`**: добавить `uploads/`.

---

## Блок B — Блокеры админки (№2, №3, №4) и загрузка файлов

**B1. Поиск (№2, А1, мелкое):** `admin/app/routers/users.py`:
- `from sqlalchemy import String, cast` → `User.telegram_id.cast(String)`;
- срезать ведущий `@` из запроса перед `ilike`;
- добавить `User.phone.ilike(...)` в условия (сбор телефона не делаем — решение заказчика);
- плейсхолдер в `users.html`: «Поиск по имени, username, телефону, ID».

**B2. Загрузка документов (№3):** `admin/app/routers/legal.py`: `document_type: str = Form(...)`.

**B3. Каталог загрузок (№4):** `UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))`. В `docker-compose.yml` env не обязателен (дефолт совпадает с volume). Для локального запуска вне Docker переменная задаётся в `.env`.

**B4. Санитайзинг загрузки (замечание 3, мелкое 4-го прохода):**
- имя на диске: `uuid4().hex + ext`, где `ext` — расширение из whitelist `{.pdf, .doc, .docx, .txt}`; оригинальное имя хранится в `file_name` (для показа);
- лимит размера 20 МБ (читать чанками, при превышении — 400);
- выдача (`/legal/{id}/download`): `media_type` по расширению (`application/pdf` и т.д.), `Content-Disposition: inline` для pdf (юр-документы должны открываться, а не скачиваться — находка 4-го прохода).

**B5. Бесплатные уроки внешней ссылкой (Т21, Т20):**
- ключ `free_lessons_url` в таблице `settings`; поле на странице `/settings` админки;
- `bot/app/services/legal.py: get_free_lessons_link` читает из settings (fallback — текущая логика по документу, затем `#`);
- из формы загрузки юр-документов тип `free_lessons` убрать (enum в БД не трогаем).

**B6. GetCourse-ссылки из настроек:** ключи `tariff_self_url`, `tariff_support_url`, `tariff_pro_url` в `settings` + поля на `/settings`. В боте helper `get_tariff_urls(session) -> dict` с дефолтами-плейсхолдерами; все клавиатуры с кнопками «Купить»/«Самостоятельный»… строятся от этих url (клавиатуры-функции принимают urls аргументом).

**B7. Миграция путей старых документов:** в `docs/migrations/2026-07-16_fixes.sql` — `UPDATE legal_documents SET file_path = replace(file_path, '/uploads/', '/app/uploads/') WHERE file_path LIKE '/uploads/%';` (файлы переносятся вручную, Блок 0 п.6).

---

## Блок C — Согласия: одна галочка + корректный отзыв (№7, доп-фикс заказчика)

**C1. Один экран согласия.** `bot/app/handlers/start.py`, `keyboards.py`:
- текст: «👋 Приветствуем в нашем боте!\n\nСогласно требований законодательства РФ, для продолжения необходимо ознакомиться и принять:\n\n📄 [Оферта](url)\n🔒 [Политика конфиденциальности](url)\n🔒 [Политика персональных данных](url)\n\nНажмите кнопку ниже, чтобы принять:»;
- одна клавиатура `consent_kb()` с кнопкой «✅ Принять» → callback `accept_all`;
- хендлер `accept_all`: ставит `consent_offer=True` и `consent_personal_data=True`, пишет ДВА `ConsentLog` (offer и personal_data, accepted=True), `funnel_stage="consent_done"`, `AnalyticsEvent("consent_accepted")`, редактирует кнопку на «✅ Принято» (noop), шлёт `CONFIRM_TEXT` + `next_kb()`;
- удалить: `get_pd_text`, `consent_offer_kb/consent_offer_done_kb/consent_pd_kb/consent_pd_done_kb` (заменить парой `consent_kb/consent_done_kb`), хендлеры `accept_offer`, `accept_pd`, `welcome_kb` (мёртвый).
- Схема users не меняется (оба boolean-флага остаются).

**C2. ConsentMiddleware ужесточить** (`bot/app/middlewares/consent.py`):
- юзер отсутствует в БД **или** без обоих согласий → пропускать только `/start` (и `/start@ИмяБота`: сравнивать `text.split()[0].split('@')[0]`) и callback `accept_all`; на всё остальное — показать консент-экран;
- анти-спам консент-экрана: в middleware держать dict `{tg_id: monotonic}` — не слать экран чаще раза в 15 сек;
- фикс `event.message is None` для CallbackQuery (проверка перед доступом к `.chat`);
- сессию БД брать из `data["session"]` (DbMiddleware регистрируется раньше), свою не открывать.

**C3. Отзыв согласия (№7):** `bot/app/handlers/consent.py: revoke_confirm`:
- до удаления юзера: `UPDATE objects SET assigned_to=NULL, status='accepted' WHERE assigned_to=:uid` (снять назначения чужих объектов — иначе FK-ошибка);
- журнал хранить (решение заказчика): миграция — `consent_log.user_id` → nullable, новая колонка `telegram_id BIGINT`; при отзыве: (а) добавить записи `ConsentLog(accepted=False, telegram_id=tid)` по обоим типам, (б) `UPDATE consent_log SET telegram_id=:tid, user_id=NULL WHERE user_id=:uid`, (в) удалить остальные данные и юзера как сейчас;
- попытаться удалить тему поддержки: `bot.delete_forum_topic(CHAT_ID, thread_id)` в try/except (персональные данные в группе — нюанс №7);
- после удаления показывать НЕ главное меню, а «🗑 Ваши данные удалены.» и следом консент-экран (пользоваться ботом без согласий нельзя).

---

## Блок D — Воронка: тексты и сценарий по ТЗ (Т1–Т5, Т9, Т12, Т17, Т19, доп-фикс «цель»)

**D1. Цель (доп-фикс заказчика).** `start.py`, `keyboards.py`:
- `GOAL_TEXT = "🎯 Какая у вас цель?"`;
- `goal_kb()`: «🏠 Продавать свои объекты» (`goal_own_objects`), «💼 Зарабатывать на роликах» (`goal_earn_money`), «🧠 Освоить нейросети» (`goal_exploring_ai`) — enum-значения прежние, БД не трогаем;
- в `goal_selected` после фиксации цели отправить персонализированный текст (дословно из «Доп фиксы» CODE_REVIEW.md, словарь по callback.data), затем «🎬 Для более чёткого представления…» и цепочку видео.

**D2. Отложенные отправки без удержания сессии БД (№12, Г2-пункт про query is too old).**
Новый модуль `bot/app/services/delayed.py`:
- `_TASKS: set[asyncio.Task]` на уровне модуля; `def run_detached(coro): t = asyncio.create_task(coro); _TASKS.add(t); t.add_done_callback(_TASKS.discard)` — заодно фикс GC (4-й проход);
- корутины цепочек НЕ получают сессию хендлера: нужные данные (chat_id, url-ы) собираются до запуска; если внутри нужна БД (кэш file_id) — короткая сессия из `shared.database.async_session_maker` на время одной отправки;
- все хендлеры с задержками (`goal_selected`, воронковые отзывы) делают `callback.answer()` СРАЗУ, затем `run_detached(...)` и выходят — сессия DbMiddleware освобождается.

**D3. Тайминги воронки примеров (Т12):** видео через 5/20/20 сек, затем **через 30 сек** «🎁 Хочешь так же? Держи 4 бесплатных урока!» + ссылка (из `free_lessons_url`) + кнопка «👀 Посмотрел».

**D4. Отзывы: 30-минутный таймер (Т1) + идемпотентность (двойной клик).**
- при отправке сообщения с кнопкой «Посмотрел» планировать APScheduler-job `reviews_{tg_id}` на now+30 мин (scheduler уже создан в `main.py`, наконец использовать);
- функция `send_funnel_reviews(bot, tg_id)`: открывает свою сессию, проверяет `funnel_stage` — если уже `watched_lessons`, выходит (защита от дубля таймер/кнопка/дабл-клик); иначе ставит `watched_lessons`, шлёт цепочку: «Наше обучение прошли уже 250 человек…» → +3с отзыв1 → +5с отзыв2 → +15с текст «150 заказов…» + кнопка «Подробнее о курсе» (тексты дословно из ТЗ);
- хендлер `watched`: `callback.answer()`, снять клавиатуру (`edit_reply_markup(None)`), отменить job `reviews_{tg_id}` (если есть), `run_detached(send_funnel_reviews(...))`;
- MemoryJobStore: таймер не переживает рестарт — осознанное допущение (зафиксировано).

**D5. «Подробнее о курсе» (Т5):** хендлер `course_detail`: текст = `ABOUT_COURSE_TEXT` (дословный из ТЗ, уже есть в menu.py — вынести в одно место) → через 15 сек `PROGRAM_TEXT` + кнопка «Узнать тарифы» (callback `compare_tariffs`). Выдуманный `COURSE_DETAIL_TEXT` и хендлер `learn_tariffs` удалить.

**D6. Тарифы дословно по ТЗ (Т2, Т3, Т4, Т17), 14 уроков:**
- три текста тарифов — дословно из `docs/TZ.md` (строки 90–129), в «Самостоятельном» — «4 модуля, **14** уроков» (подтверждено заказчиком);
- каждое тарифное сообщение — со своей клавиатурой: «Купить за X ₽» (url из настроек), «📊 Сравнить тарифы» (`compare_tariffs` — на самих тарифных: листает к таблице; чтобы не зациклить, в `compare_tariffs` кнопку «Сравнить тарифы» на тарифных сообщениях заменяем на отсутствие — см. ниже), «✍️ Задать вопрос» (`ask_question`);
  - упрощение против зацикливания: `compare_tariffs` шлёт 3 тарифных сообщения (кнопки: «Купить за X ₽», «Задать вопрос»), затем фото-таблицу, затем отдельное сообщение «Выберите тариф» с кнопками «Самостоятельный»/«С поддержкой»/«PRO» (url), «✍️ Задать вопрос», «🏠 Главное меню» (`tariff_select_kb` + добавить «Задать вопрос» — Т4);
- паузы `sleep(1)` между тарифными сообщениями убрать (ТЗ: «затем сразу»);
- `menu_enroll` («Записаться на курс»): «Выберите тариф» + `tariff_select_kb` (как сейчас, с «Подробнее о тарифах»); дубль-callback `enroll` удалить, в `after_examples_kb` использовать `menu_enroll`;
- старую `tariffs_kb` удалить.

**D7. `/start`, `/menu`, навигация (Т15, Т16, Т11, funnel_stage):**
- `cmd_start`: первым делом `state.clear()`; без согласий → консент-экран; с согласиями → «🏠 Главное меню» + `main_menu_kb()` — интро повторно НЕ гонять, `funnel_stage` НЕ трогать;
- новая команда `/menu` → то же меню + `state.clear()`;
- `main_menu_callback` (`menu.py`): добавить `state: FSMContext` и `state.clear()` — чинит №6 («Отмена» вопроса) и все выходы в меню;
- неизвестные команды (`F.text.startswith("/")`, кроме известных): ответ «Не знаю такой команды. /menu — главное меню.» (сейчас молча глотаются);
- `funnel_stage` двигать только вперёд: helper `advance_stage(user, stage)` в `shared/` со словарём порядка `start < consent_done < intro_done < goal_selected < free_lessons_sent < watched_lessons < …`; все присвоения `funnel_stage` в боте — через него (аналитика воронки, 4-й проход).

**D8. Меню «Примеры работ» (Т8):** отдельная функция для меню: 3 видео подряд БЕЗ задержек (но через `run_detached`, т.к. первая загрузка файлов долгая) → кнопки «🎓 Записаться на курс» (`menu_enroll`), «🏠 Главное меню». Текст «Держи 4 урока» в меню-версии не шлётся. `callback.answer()` — сразу. Дубль-callback `examples` удалить.

**D9. Меню «Отзывы» (Т9, решение заказчика — строго по ТЗ):** только отзыв1 → +5с отзыв2 → кнопка «🏠 Главное меню». Без «250 человек» и «150 заказов». Полная версия остаётся только в воронке (`send_funnel_reviews`).

**D10. ЧаВо (Т18):** после текста — одна кнопка «🏠 Главное меню» (не всё меню).

**D11. Сверка текстов (Т19):** `CONFIRM_TEXT` и остальные тексты воронки привести дословно к ТЗ (в т.ч. пункт «концентрат знаний от людей, которые не просто сделали видео ради показухи…» — полная формулировка). Эмодзи-оформление сохранить, слова — из ТЗ.

---

## Блок E — Анкета объекта (№5, Т6) и статус заказов (Т10)

**E1. Модель:** `objects.object_name` → `nullable=True`; новая колонка `cancelled = Column(Boolean, default=False, nullable=False)`. Миграция в SQL-файле.

**E2. FSM-анкета** (`bot/app/handlers/object.py`):
- на каждом шаге клавиатура: обязательные шаги (название, адрес, описание, бюджет) — кнопка «❌ Отмена» (`obj_cancel`); необязательные (фото, видео) — «➡️ Далее» (`obj_skip`, записывает пустое значение и идёт дальше) и «❌ Отмена»;
- все текстовые шаги — фильтр `F.text`; на не-текст в состоянии анкеты — отдельный хендлер: «Пожалуйста, отправьте текстовое сообщение» (чинит IntegrityError с фото);
- после ввода бюджета — сводка введённого + кнопки «✅ Отправить» (`obj_submit`) и «❌ Отмена» (по ТЗ последний шаг — «отправить и отмена»);
- `obj_submit`: сохраняет `Object(status=accepted, cancelled=False)`, `state.clear()`, «✅ Объект принят! Мы свяжемся с вами.» + главное меню;
- `obj_cancel`: если введено хоть одно поле — сохранить частичный `Object(cancelled=True, status=accepted)`; если ничего — не сохранять; `state.clear()`, главное меню;
- «нет»-логика на фото/видео остаётся как дополнение к кнопке «Далее».

**E3. Статус «Принят» (Т10):** новые объекты создавать со `status=ObjectStatusEnum.accepted`; в русификации админки `accepted` = «Принят». `pending` больше не используется (enum не трогаем).

**E4. Пометка отмены в админке:** в списке объектов и карточке — если `cancelled`: `<span style="color:red;font-weight:bold">ПОЛЬЗОВАТЕЛЬ ОТМЕНИЛ</span>`. Частично заполненные поля выводить как есть (пустые — «—»).

---

## Блок F — Вопросы и группа поддержки (№6, Т13, Т14, замечания 4, 7, 5-й проход)

**F1. Единый сервис поддержки** — новый `bot/app/services/support_service.py`:
- `async def ensure_thread(bot, session, user) -> int`: возвращает `support_thread_id`; если нет — создаёт тему `create_forum_topic` (имя: `{first_name} {last_name или ''} (@username / id)`), сохраняет, коммитит; от гонки двух тем — `asyncio.Lock` per-user (dict tg_id→Lock на уровне модуля);
- `async def deliver_to_support(bot, session, user, message) -> bool`: получает thread через `ensure_thread`, делает `message.copy_to(chat_id=CHAT_ID, message_thread_id=thread)`; при `TelegramBadRequest` с "thread not found"/"TOPIC_CLOSED"/"message thread not found" — обнуляет `support_thread_id`, пересоздаёт тему, повторяет один раз (чинит «закрытая тема отрезает юзера», 5-й проход);
- вся тройная копипаста в `question.py` заменяется вызовами этого сервиса.

**F2. «Задать вопрос» по ТЗ (Т13):**
- текст: «✍️ Введите свой вопрос. Ответ поступит в этот же бот.», кнопки «📤 Отправить» и «❌ Отмена»;
- «Отмена» → `main_menu` (state теперь чистится там, №6 закрыт);
- «Отправить» до ввода текста → `callback.answer("Сначала введите текст вопроса", show_alert=True)`;
- после ввода текста: сохранить в state, показать «Ваш вопрос: …» + «📤 Отправить» (`question_send`) / «❌ Отмена»;
- `question_send`: пишет `Question`, доставляет через `deliver_to_support`, `state.clear()`, «✅ Вопрос отправлен…» + одна кнопка «Главное меню» (Т18-паттерн).

**F3. Автопересылка любых типов (Т14):** хендлер-ловушка вне состояний принимает `text | photo | video | document | voice | video_note | sticker | audio` (единый `@router.message(...)` без F-фильтра по типу, после всех остальных роутеров) и шлёт через `deliver_to_support` (`copy_to` универсален). Команды (`/...`) — исключить (их ловит D7-хендлер).

**F4. Ответы админов (замечание 7):** `support.py`: заменить ветвление по типам на `copy_message` в чат юзера — работает для голосовых/кружков/стикеров; при ошибке отправки — reply в тему «⚠️ Не доставлено: {ошибка}» вместо `except: pass`.

---

## Блок G — Рассылки и уведомления (№8, №9, №10, №11, 4–5-й проходы)

**G1. Один механизм уведомлений о назначении (№8):** остаётся `shared/notifier.py` (вызов из админки). Удалить: `check_new_orders` из `bot/app/services/mailing.py`, весь `bot/app/services/notification.py`.

**G2. Notifier (№13 + мелкое 3-го прохода):** `html.escape()` на все подставляемые поля; таймаут HTTP 5 сек; вызов из роутера админки — в `BackgroundTasks` FastAPI (страница не висит 30 сек).

**G3. Таймзона (№9 + даты в админке):**
- в `shared/config.py`: `TZ = ZoneInfo("Europe/Moscow")`;
- админка при сохранении рассылки: интерпретировать `datetime-local` как МСК → конвертировать в naive UTC для хранения;
- jinja-фильтр `msk` (UTC→МСК, формат `%d.%m.%Y %H:%M`) — применить ко ВСЕМ выводам дат во всех шаблонах.

**G4. Цикл рассылок (№10, 4–5-й проходы):**
- `bot/app/main.py`: `mailing_task = asyncio.create_task(mailing_loop(bot))` — держать ссылку;
- при старте бота: `UPDATE mailings SET status='pending' WHERE status='sending'` (возобновление после рестарта);
- в отправке: `asyncio.sleep(0.05)` между сообщениями; `except TelegramRetryAfter as e: await asyncio.sleep(e.retry_after); повторить один раз`;
- итог: `sent_count`, `failed_count`; статус `error` если `sent_count == 0 and failed_count > 0`, иначе `sent`;
- сессию БД в цикле держать только на выборку получателей/запись логов, не на время всех отправок (собрать список получателей заранее, логи писать батчем в конце).

**G5. Админка рассылок:**
- «Повторить» (№11): параметры через `urllib.parse.urlencode`;
- в списке рассылок — колонка «Доставлено / Ошибок» (агрегат по `mailing_logs`);
- защита от двойного сабмита: `onsubmit` → disable кнопки (во всех формах создания).

---

## Блок H — Админка: объекты, пользователи, аналитика (№14, А2–А5)

**H1. ФИО-helper (№14):** jinja-глобал/функция `full_name(user)` = `first_name + (' ' + last_name if last_name else '')`; применить в `objects.py:127` (скачивание карточки) и всех шаблонах (убрать «Иван None»).

**H2. Назначение объекта (А2):** `<input list="users-list">` + `<datalist>` со всеми юзерами (`id — @username — Имя`); POST: если пользователь не найден — redirect с `?error=user_not_found` и показ ошибки на странице (сейчас молча).

**H3. Взаимоисключение статусов (А3):** POST-эндпоинты назначения/отклонения проверяют текущий статус: нельзя отклонить `assigned`, нельзя назначить `rejected` (сначала вернуть в «Принят»); нарушение → 400/redirect с ошибкой. Кнопка «Вернуть в Принят» для отклонённых/назначенных.

**H4. Аналитика воронки (А4):** на дашборде — таблица по `funnel_stage` в порядке воронки (counts из users) + конверсия к предыдущему этапу. Достоверность обеспечивает D7 (advance-only).

**H5. Русификация users.html:** цель и этап воронки — через существующий словарь переводов (как в карточке).

**H6. Пагинация (замечание 10):** users/objects/mailings — `?page=N`, 50 строк, ссылки «← Назад / Вперёд →».

**H7. Карточка пользователя:** вывести `mailing_logs` (дата, рассылка, статус) — данные уже грузятся.

**H8. Авторизация (замечание 2):** `secrets.compare_digest` для пароля; `asyncio.sleep(1)` при неверном пароле; cookie: `samesite="lax"`, `secure=True`; `@app.on_event` → lifespan.

---

## Блок I — Надёжность и чистка

**I1. Кэш file_id по пути+mtime (5-й проход, мина под Фазу 3):**
- `cached_files`: новая колонка `file_mtime FLOAT`; выборка по `file_path`, если `file_mtime` в БД ≠ `os.path.getmtime` — перезаливка файла;
- запись — upsert `INSERT ... ON CONFLICT (file_path) DO UPDATE SET file_id=..., file_mtime=...` (`sqlalchemy.dialects.postgresql.insert`) — заодно чинит гонку двух пользователей на холодном кэше.

**I2. `get_or_create_user`:** обновлять `username/first_name/last_name` при каждом заходе, если изменились; гонка INSERT — `try/except IntegrityError → rollback → повторный select`.

**I3. Мёртвый код — удалить:** `welcome_kb`, старую `tariffs_kb`, `learn_tariffs`, `services/notification.py`, дубли callback `examples`/`enroll`, `SECRET_KEY` и `get_current_user` в `dependencies.py`, монтирование `StaticFiles` + `style.css` (стили инлайн в base.html — оставить как есть), неиспользуемые импорты по всем правленым файлам.

**I4. FSM-хранилище:** остаёмся на `MemoryStorage` — осознанно. Риски снижены: `/start`, `/menu` чистят state; анкета/вопрос короткие. Redis не вводим (лишний сервис). Зафиксировано в Журнале решений.

**I5. `docs/ARCHITECTURE.md`:** переписать по факту: `shared/` (config/database/models), реальные модули бота и админки, порты 127.0.0.1, схема уведомлений (только notifier), consent-флоу одной галочкой.

**I6. Мусор в репо:** неиспользуемые медиа (`ждун.jpg`, `бабка на рынке.jpg`, `долбит в окно.mov`, `лёд.mov`, `труба с водой.mov`), `.mimocode/.cron-lock` — удалить (git-часть — пользователь). Дубли-заглушки отзывов (`отзыв_анна.jpg` = `бабка на рынке.jpg`) — заменить при загрузке реального контента (Фаза 3).

---

## SQL-миграция (создать `docs/migrations/2026-07-16_fixes.sql`)

```sql
ALTER TABLE objects ALTER COLUMN object_name DROP NOT NULL;
ALTER TABLE objects ADD COLUMN IF NOT EXISTS cancelled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE consent_log ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE consent_log ADD COLUMN IF NOT EXISTS telegram_id BIGINT;
ALTER TABLE cached_files ADD COLUMN IF NOT EXISTS file_mtime DOUBLE PRECISION;
UPDATE legal_documents SET file_path = replace(file_path, '/uploads/', '/app/uploads/')
  WHERE file_path LIKE '/uploads/%';
UPDATE mailings SET status = 'pending' WHERE status = 'sending';
DELETE FROM cached_files;  -- перед заменой контента на реальный (Фаза 3)
```

На свежей БД `create_all` создаст всё сам; миграция — для существующей прод-БД.

---

## Порядок реализации и исполнители

| Шаг | Блоки | Исполнитель | Зачем в этом порядке |
|---|---|---|---|
| 1 | A + B | coder | Безопасность и блокеры админки; независимы от бота |
| 2 | C | coder | Консент — фундамент всех сценариев бота |
| 3 | D | coder | Воронка (самый большой блок, тексты дать в ТЗ дословно) |
| 4 | E + F | coder | Анкета и поддержка (общий сервис support_service) |
| 5 | G | coder | Рассылки/уведомления |
| 6 | H | coder-simple → coder | Шаблоны/русификация/пагинация — simple; логика статусов/аналитика — coder |
| 7 | I | coder-simple (I3, I5, I6) + coder (I1, I2) | Чистка и надёжность |

Каждому сабагенту в ТЗ: полные тексты сообщений (дословно), сигнатуры функций, запрет git-операций и правки STATE/PLAN. После каждого шага — проверка оркестратором и отметка в PLAN.md.
