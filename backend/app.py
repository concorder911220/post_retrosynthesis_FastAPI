import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import engine, Base
from models import HealthResponse
from routes import search, results, update

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield

    logger.info("Shutting down...")


app = FastAPI(
    title="Retrosynthesis Backend API",
    description="Backend API for retrosynthesis search requests",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy")


app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(results.router, prefix="/api", tags=["results"])
app.include_router(update.router, prefix="/api", tags=["update"])
