from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db
from routers import categories, habits, events, admin, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Lock In", lifespan=lifespan)

app.include_router(categories.router)
app.include_router(habits.router)
app.include_router(events.router)
app.include_router(admin.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
