import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from shared.database import init_db
from .routers import auth, dashboard, users, mailings, objects, legal, settings

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Admin Panel")

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(mailings.router)
app.include_router(objects.router)
app.include_router(legal.router)
app.include_router(settings.router)


@app.on_event("startup")
async def startup():
    await init_db()
    app.state.admin_token = None
