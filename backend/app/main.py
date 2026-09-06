from fastapi import FastAPI
from sqlalchemy import text

from backend.app.api.v1.health import router as health_router
from backend.app.config import get_settings
from backend.app.database import engine
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.steganalysis import router as steganalysis_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.datasets import router as datasets_router
from backend.app.api.v1.optimization_runs import router as optimization_runs_router
from backend.app.api.v1.optimization_iterations import router as optimization_iterations_router
from backend.app.api.v1.candidate_configurations import router as candidate_configurations_router
from backend.app.api.v1.objective_scores import router as objective_scores_router
from backend.app.api.v1.steganography_sessions import (
    router as steganography_sessions_router,
)
from backend.app.api.v1.payloads import router as payloads_router


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)


app.include_router(health_router)
app.include_router(users_router)
app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(optimization_runs_router)
app.include_router(optimization_iterations_router)
app.include_router(candidate_configurations_router)
app.include_router(objective_scores_router)
app.include_router(steganography_sessions_router)
app.include_router(payloads_router)
app.include_router(steganalysis_router)


@app.get("/health/db")
def database_health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }