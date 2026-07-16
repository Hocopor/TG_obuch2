import asyncio

_TASKS: set[asyncio.Task] = set()


def run_detached(coro):
    """Запускает корутину отдельной задачей, держит ссылку (иначе GC может убить), чистит по завершении."""
    task = asyncio.create_task(coro)
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return task
