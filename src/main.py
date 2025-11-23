"""
Permía Backend - Main Application
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import text

from .api import evidence, exports, applications, facts, snapshots, evaluation
from .core.config import settings
from .core.database import engine
from .core.correlation import CorrelationIdMiddleware
from .core.rate_limit import RateLimitMiddleware
from .core.logging_config import setup_logging
from .services.storage import storage_service

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize Sentry if configured
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        )
        logger.info("Sentry monitoring initialized", extra={"correlation_id": "startup"})
    except ImportError:
        logger.warning("Sentry SDK not installed, monitoring disabled", extra={"correlation_id": "startup"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup/shutdown"""
    logger.info("=" * 80, extra={"correlation_id": "startup"})
    logger.info("Permía Backend starting...", extra={"correlation_id": "startup"})
    logger.info(f"Environment: {settings.ENVIRONMENT}", extra={"correlation_id": "startup"})
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1]}", extra={"correlation_id": "startup"})
    logger.info(f"Auth Required: {settings.AUTH_REQUIRED}", extra={"correlation_id": "startup"})
    logger.info(f"Rate Limiting: {settings.RATE_LIMIT_ENABLED}", extra={"correlation_id": "startup"})
    logger.info(f"Export API: {settings.ENABLE_EXPORT_API}", extra={"correlation_id": "startup"})
    logger.info("=" * 80, extra={"correlation_id": "startup"})

    # Verify database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified", extra={"correlation_id": "startup"})
    except Exception as e:
        logger.error(f"Database connection failed: {e}", extra={"correlation_id": "startup"})

    # Verify storage connection
    try:
        if storage_service.check_health():
            logger.info("Storage connection verified", extra={"correlation_id": "startup"})
        else:
            logger.warning("Storage health check failed", extra={"correlation_id": "startup"})
    except Exception as e:
        logger.error(f"Storage connection failed: {e}", extra={"correlation_id": "startup"})

    yield
    logger.info("Permía Backend shutting down...", extra={"correlation_id": "shutdown"})


app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_REDOC else None,
)


def custom_openapi():
    """Custom OpenAPI schema with security definitions"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.API_TITLE,
        version="0.1.0",
        description=settings.API_DESCRIPTION,
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

    # Apply security to all endpoints
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            if isinstance(operation, dict) and "tags" in operation:
                operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Middleware (order matters!)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        rate_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        rate_per_hour=settings.RATE_LIMIT_PER_HOUR,
    )

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-Id", "X-RateLimit-Remaining-Minute", "X-RateLimit-Remaining-Hour"],
)

# Include routers
app.include_router(
    evidence.router,
    prefix=f"/api/{settings.API_VERSION}/evidence",
    tags=["Evidence"],
)

if settings.ENABLE_EXPORT_API:
    app.include_router(
        exports.router,
        prefix=f"/api/{settings.API_VERSION}/exports",
        tags=["Exports"],
    )

# Application management endpoints
app.include_router(
    applications.router,
    tags=["Applications"],
)

# Facts endpoints (nested under applications)
app.include_router(
    facts.router,
    tags=["Facts"],
)

# Decision snapshots endpoints
app.include_router(
    snapshots.router,
    tags=["Snapshots"],
)

# Evaluation endpoints (nested under applications)
app.include_router(
    evaluation.router,
    tags=["Evaluation"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check with DB and storage verification

    Returns 200 if healthy, 503 if unhealthy
    """
    health = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
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
        logger.error(f"Health check: database unhealthy: {e}", extra={"correlation_id": "health"})

    try:
        if storage_service.check_health():
            health["storage"] = "connected"
        else:
            health["storage"] = "disconnected"
            health["status"] = "degraded"
            logger.warning("Health check: storage disconnected", extra={"correlation_id": "health"})
    except Exception as e:
        health["storage"] = f"error: {str(e)}"
        health["status"] = "degraded"
        logger.error(f"Health check: storage error: {e}", extra={"correlation_id": "health"})

    # Return 503 if unhealthy (K8s will restart pod)
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)


@app.get("/", tags=["System"])
async def root():
    """Root endpoint"""
    return {
        "service": settings.API_TITLE,
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.ENABLE_DOCS else None,
        "health": "/health",
    }
