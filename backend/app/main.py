"""Main FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import time
import os

from app.config import settings
from app.database import init_db
from app.api import flights, stats, airlines

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    Flight Intelligence API - A comprehensive platform for flight tracking and analysis.
    """,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Add error handling middleware
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    """Catch and log exceptions."""
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# Include routers
app.include_router(flights.router)
app.include_router(stats.router)
app.include_router(airlines.router)

@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "healthy"}

# Serve frontend
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{catchall:path}")
    async def serve_frontend(catchall: str):
        # Prevent path traversal
        file_path = os.path.abspath(os.path.join(frontend_dist, catchall))
        if file_path.startswith(frontend_dist) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Otherwise serve index.html
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "Frontend not found"}
else:
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs" if settings.DEBUG else None
        }