# Линейный порядок этапов воронки. funnel_stage двигается только вперёд.
STAGE_ORDER = [
    "start",
    "consent_done",
    "intro_done",
    "goal_selected",
    "free_lessons_sent",
    "watched_lessons",
    "course_detail",
    "tariffs_viewed",
    "object_submitted",
]


def advance_stage(user, stage: str) -> None:
    """Двигает user.funnel_stage вперёд по STAGE_ORDER. Назад и на неизвестные стадии — не двигает."""
    if stage not in STAGE_ORDER:
        return
    cur = STAGE_ORDER.index(user.funnel_stage) if user.funnel_stage in STAGE_ORDER else -1
    new = STAGE_ORDER.index(stage)
    if new > cur:
        user.funnel_stage = stage
