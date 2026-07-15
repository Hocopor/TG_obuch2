from aiogram import Router
from .start import router as start_router
from .menu import router as menu_router
from .course import router as course_router
from .examples import router as examples_router
from .reviews import router as reviews_router
from .faq import router as faq_router
from .support import router as support_router
from .object import router as object_router
from .question import router as question_router
from .consent import router as consent_router


def register_handlers(router: Router):
    router.include_router(start_router)
    router.include_router(menu_router)
    router.include_router(course_router)
    router.include_router(examples_router)
    router.include_router(reviews_router)
    router.include_router(faq_router)
    router.include_router(support_router)
    router.include_router(object_router)
    router.include_router(question_router)
    router.include_router(consent_router)
