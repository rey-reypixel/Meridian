from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import routes, auth
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Schema is provisioned via Alembic (`alembic upgrade head`), not at import
# time. See app/db/database.py::init_db for the dev-only create_all() escape
# hatch, kept for convenience but no longer called automatically.

# Create FastAPI app
app = FastAPI(
    title="Meridian",
    description="LLM Cost Optimization Engine",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("Meridian API starting up")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Optimizations enabled: "
                f"context_truncation={settings.context_truncation_enabled}, "
                f"model_routing={settings.model_routing_enabled}, "
                f"batch_processing={settings.batch_processing_enabled}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Meridian API shutting down")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Meridian",
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Meridian",
        "description": "LLM Cost Optimization Engine",
        "version": "0.1.0",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


# Include routers
app.include_router(auth.router)
app.include_router(routes.router)

logger.info("Meridian API initialized successfully")
