from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app.routes import health, chat, actions, context, reminders
from app.mcp.mcp_server import mcp_asgi_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="ActionFlow backend with Amazon Bedrock integration and self-hosted MCP Server",
    lifespan=lifespan
)

# CORS configuration
allowed_origins = [settings.FRONTEND_ORIGIN.rstrip("/")]
# Support default Next.js local development variations if configured
for default_origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
    if default_origin not in allowed_origins:
        allowed_origins.append(default_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(actions.router)
app.include_router(context.router)
app.include_router(reminders.router)

# Mount self-hosted MCP Server over Streamable HTTP at /mcp
app.mount("/mcp", mcp_asgi_app)
