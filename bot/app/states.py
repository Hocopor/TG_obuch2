from aiogram.fsm.state import State, StatesGroup


class QuestionState(StatesGroup):
    waiting_text = State()


class ObjectState(StatesGroup):
    waiting_name = State()
    waiting_address = State()
    waiting_description = State()
    waiting_photos = State()
    waiting_videos = State()
    waiting_budget = State()
