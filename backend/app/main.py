from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, documents, sessions
from app.config import settings
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version="1.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "1.3.0",
    }