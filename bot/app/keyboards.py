from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb():
    """Главное меню — инлайн-кнопки в сообщении."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📚 Бесплатные материалы", callback_data="menu_free_materials"))
    builder.row(InlineKeyboardButton(text="🎓 Записаться на курс", callback_data="menu_enroll"))
    builder.row(
        InlineKeyboardButton(text="ℹ️ О курсе", callback_data="menu_about"),
        InlineKeyboardButton(text="📋 Программа", callback_data="program")
    )
    builder.row(
        InlineKeyboardButton(text="🎬 Примеры работ", callback_data="menu_examples"),
        InlineKeyboardButton(text="💬 Отзывы", callback_data="reviews")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Частые вопросы", callback_data="faq"),
        InlineKeyboardButton(text="✍️ Задать вопрос", callback_data="ask_question")
    )
    builder.row(InlineKeyboardButton(text="🏠 Предложить свой объект", callback_data="start_object"))
    builder.row(InlineKeyboardButton(text="🚫 Отозвать согласие на обработку ПНд", callback_data="revoke_start"))
    return builder.as_markup()


def consent_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Принять", callback_data="accept_all"))
    return builder.as_markup()


def consent_done_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Принято", callback_data="noop"))
    return builder.as_markup()


def home_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def next_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👉 Далее", callback_data="next_intro"))
    return builder.as_markup()


def goal_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Продавать свои объекты", callback_data="goal_own_objects"))
    builder.row(InlineKeyboardButton(text="💼 Зарабатывать на роликах", callback_data="goal_earn_money"))
    builder.row(InlineKeyboardButton(text="🧠 Освоить нейросети", callback_data="goal_exploring_ai"))
    return builder.as_markup()


def watched_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👀 Посмотрел", callback_data="watched"))
    return builder.as_markup()


def course_detail_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📖 Подробнее о курсе", callback_data="course_detail"))
    return builder.as_markup()


def tariff_msg_kb(buy_url: str, price: str):
    """Клавиатура под каждым тарифным сообщением внутри «Сравнить тарифы»."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"Купить за {price} ₽", url=buy_url))
    builder.row(InlineKeyboardButton(text="✍️ Задать вопрос", callback_data="ask_question"))
    return builder.as_markup()


def tariff_select_kb(urls: dict):
    """«Выберите тариф» для раздела «Записаться на курс» (menu_enroll)."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Самостоятельный", url=urls["self"]))
    builder.row(InlineKeyboardButton(text="С поддержкой", url=urls["support"]))
    builder.row(InlineKeyboardButton(text="PRO", url=urls["pro"]))
    builder.row(InlineKeyboardButton(text="📊 Подробнее о тарифах", callback_data="compare_tariffs"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def tariff_final_kb(urls: dict):
    """«Выберите тариф» в конце «Сравнить тарифы» (без «Подробнее» — чтобы не зациклить)."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Самостоятельный", url=urls["self"]))
    builder.row(InlineKeyboardButton(text="С поддержкой", url=urls["support"]))
    builder.row(InlineKeyboardButton(text="PRO", url=urls["pro"]))
    builder.row(InlineKeyboardButton(text="✍️ Задать вопрос", callback_data="ask_question"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def learn_tariffs_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💰 Узнать тарифы", callback_data="compare_tariffs"))
    return builder.as_markup()


def confirm_revoke_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data="revoke_confirm"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu"))
    return builder.as_markup()


def question_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu"))
    return builder.as_markup()


def obj_cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="obj_cancel"))
    return builder.as_markup()


def obj_skip_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➡️ Далее", callback_data="obj_skip"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="obj_cancel"))
    return builder.as_markup()


def obj_submit_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Отправить", callback_data="obj_submit"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="obj_cancel"))
    return builder.as_markup()


def after_examples_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎓 Записаться на курс", callback_data="menu_enroll"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def about_course_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Программа курса", callback_data="program"))
    builder.row(InlineKeyboardButton(text="💰 Тарифы", callback_data="compare_tariffs"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def program_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎓 Записаться на курс", callback_data="menu_enroll"))
    builder.row(InlineKeyboardButton(text="💰 Тарифы", callback_data="compare_tariffs"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()
