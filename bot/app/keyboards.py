from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Бесплатные материалы"))
    builder.row(KeyboardButton(text="Записаться на курс"))
    builder.row(KeyboardButton(text="О курсе"), KeyboardButton(text="Программа"))
    builder.row(KeyboardButton(text="Примеры работ"), KeyboardButton(text="Отзывы"))
    builder.row(KeyboardButton(text="Частые вопросы"), KeyboardButton(text="Задать вопрос"))
    builder.row(KeyboardButton(text="Предложить свой объект"))
    builder.row(KeyboardButton(text="Отозвать согласие на обработку ПНд"))
    return builder.as_markup(resize_keyboard=True)


def welcome_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="/start", callback_data="start"))
    return builder.as_markup()


def consent_offer_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Принять", callback_data="accept_offer"))
    return builder.as_markup()


def consent_pd_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Принять", callback_data="accept_pd"))
    return builder.as_markup()


def next_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Далее", callback_data="next_intro"))
    return builder.as_markup()


def goal_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Хочу делать ролики для своих объектов", callback_data="goal_own_objects"))
    builder.row(InlineKeyboardButton(text="Хочу зарабатывать на создании роликов", callback_data="goal_earn_money"))
    builder.row(InlineKeyboardButton(text="Пока просто изучаю нейросети", callback_data="goal_exploring_ai"))
    return builder.as_markup()


def watched_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Посмотрел", callback_data="watched"))
    return builder.as_markup()


def course_detail_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Подробнее о курсе", callback_data="course_detail"))
    return builder.as_markup()


def tariffs_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Купить за 7 900 ₽", url="https://getcourse.example.com/self"))
    builder.row(InlineKeyboardButton(text="Купить за 10 900 ₽", url="https://getcourse.example.com/support"))
    builder.row(InlineKeyboardButton(text="Купить за 14 900 ₽", url="https://getcourse.example.com/pro"))
    builder.row(InlineKeyboardButton(text="Сравнить тарифы", callback_data="compare_tariffs"))
    builder.row(InlineKeyboardButton(text="Задать вопрос", callback_data="ask_question"))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def tariff_select_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Самостоятельный", url="https://getcourse.example.com/self"))
    builder.row(InlineKeyboardButton(text="С поддержкой", url="https://getcourse.example.com/support"))
    builder.row(InlineKeyboardButton(text="PRO", url="https://getcourse.example.com/pro"))
    builder.row(InlineKeyboardButton(text="Подробнее о тарифах", callback_data="compare_tariffs"))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def confirm_revoke_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Подтвердить", callback_data="revoke_confirm"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="main_menu"))
    return builder.as_markup()


def send_question_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отправить", callback_data="send_question"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="main_menu"))
    return builder.as_markup()


def object_step_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Далее", callback_data="obj_next"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="obj_cancel"))
    return builder.as_markup()


def object_send_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отправить", callback_data="obj_send"))
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="obj_cancel"))
    return builder.as_markup()


def after_examples_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Записаться на курс", callback_data="enroll"))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def about_course_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Программа курса", callback_data="program"))
    builder.row(InlineKeyboardButton(text="Тарифы", callback_data="compare_tariffs"))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def program_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Записаться на курс", callback_data="enroll"))
    builder.row(InlineKeyboardButton(text="Тарифы", callback_data="compare_tariffs"))
    builder.row(InlineKeyboardButton(text="Главное меню", callback_data="main_menu"))
    return builder.as_markup()
