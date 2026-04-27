from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, files, ingest, lint, wiki
from app.api import schema as schema_api
from app.core.config import settings

app = FastAPI(
    title="LLM Wiki API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(wiki.router)
app.include_router(chat.router)
app.include_router(lint.router)
app.include_router(files.router)
app.include_router(schema_api.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}
