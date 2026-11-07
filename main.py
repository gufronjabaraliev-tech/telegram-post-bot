import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import PORT, HOST, UPLOAD_DIR, BASE_DIR
from app.database import init_db
from app.routes import router
from app.bot import bot_polling_worker
from app.scheduler import scheduled_posts_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app")

bot_task = None
scheduler_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("⚡ Ilova ishga tushmoqda...")
    init_db()
    
    # Launch background workers
    global bot_task, scheduler_task
    bot_task = asyncio.create_task(bot_polling_worker())
    scheduler_task = asyncio.create_task(scheduled_posts_worker())

    yield

    # Shutdown
    logger.info("🛑 Ilova to'xtatilmoqda...")
    if bot_task:
        bot_task.cancel()
    if scheduler_task:
        scheduler_task.cancel()

app = FastAPI(title="Telegram Mini App Post Publisher", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    return FileResponse(str(BASE_DIR / "static" / "index.html"))

if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
