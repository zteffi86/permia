from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from sqlalchemy import text

from .api import evidence
from .core.config import settings
from .core.database import engine
from .core.correlation import CorrelationIdMiddleware
from .services.storage import storage_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup/shutdown"""
    print("=€ Permía Backend starting...")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database: {settings.DATABASE_URL.split('@')[-1]}")
    yield
    print("=K Permía Backend shutting down...")


app = FastAPI(
    title="Permía API",
    description="Deterministic enforcement infrastructure for regulated industries",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


def custom_openapi():
    """Custom OpenAPI schema with security definitions"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Permía API",
        version="0.1.0",
        description="Deterministic enforcement infrastructure for regulated industries",
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token from authentication provider (optional in dev mode)",
        }
    }

    # Apply security to all endpoints (optional enforcement)
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            if isinstance(operation, dict) and "tags" in operation:
                operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-Id"],
)

# Include routers
app.include_router(
    evidence.router,
    prefix="/api/v1/evidence",
    tags=["Evidence"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check with DB and storage verification"""
    health = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "unknown",
        "storage": "unknown",
    }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health["database"] = "connected"
    except Exception as e:
        health["database"] = f"disconnected: {str(e)}"
        health["status"] = "unhealthy"

    try:
        if storage_service.check_health():
            health["storage"] = "connected"
        else:
            health["storage"] = "disconnected"
            health["status"] = "degraded"
    except Exception as e:
        health["storage"] = f"error: {str(e)}"
        health["status"] = "degraded"

    return health


@app.get("/", tags=["System"])
async def root():
    """Root endpoint"""
    return {
        "service": "Permía API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
