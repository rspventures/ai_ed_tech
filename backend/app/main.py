"""
AI Tutor Platform - FastAPI Application
Main application entry point with middleware and route configuration
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import init_db, run_sql_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    
    # Initialize OpenTelemetry for Agent Observability
    try:
        from app.ai.core.telemetry import init_telemetry
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        
        init_telemetry()
        FastAPIInstrumentor.instrument_app(app)
        print("[Startup] OpenTelemetry initialized for agent observability")
    except Exception as e:
        print(f"[Startup] Telemetry initialization skipped: {e}")
    
    # Initialize database tables
    await init_db()
    print("[Startup] Database tables initialized")
    
    # Run SQL migrations (additive scripts that depend on base tables)
    await run_sql_migrations()
    print("[Startup] SQL migrations executed")

    # Initialize Langfuse Observability
    try:
        from app.ai.core import init_observability
        init_observability()
    except Exception as e:
        print(f"[Startup] Langfuse initialization failed: {e}")
    
    # Auto-seed curriculum if database is empty (first deployment)
    try:
        from sqlalchemy import select, func
        from app.core.database import async_session_maker
        from app.models.curriculum import Subject
        
        async with async_session_maker() as session:
            result = await session.execute(select(func.count(Subject.id)))
            subject_count = result.scalar()
            
            if subject_count == 0:
                print("[Startup] No subjects found - seeding CBSE curriculum data...")
                from app.scripts.seed_curriculum_cbse_full import seed_full_curriculum
                await seed_full_curriculum()
                print("[Startup] ✓ Full CBSE curriculum seeding complete!")
            else:
                print(f"[Startup] Curriculum already seeded ({subject_count} subjects found)")
    except Exception as e:
        print(f"[Startup] Auto-seed check failed (non-fatal): {e}")
    
    yield
    
    # Shutdown
    pass



def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered learning platform for personalized education",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    # Add a specific health check for API v1 prefix to satisfy Nginx/Frontend expectations
    @app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
    async def api_v1_health_check():
        """API V1 Health check."""
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
