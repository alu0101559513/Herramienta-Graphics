from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.core.config import settings
from server.db.database import init_db
from server.routers import analysis, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Description:
        Initialize the application lifespan and prepare the database before
        serving requests.

    Args:
        app (FastAPI): FastAPI application instance.

    Returns:
        None: Yields control back to FastAPI after database initialization.
    """

    await init_db()
    yield


app = FastAPI(
    title="Benchmark Analysis API",
    description="API for benchmarking algorithms using SAES",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """
    Description:
        Return a simple health check message for the API root.

    Args:
        None.

    Returns:
        dict[str, str]: A status payload confirming the API is running.
    """

    return {"message": "Benchmark Analysis API is running"}


app.include_router(auth.router)
app.include_router(analysis.router)
