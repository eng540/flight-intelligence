"""Main FastAPI application."""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import time
import os
import mimetypes

from app.config import settings
from app.database import init_db
from app.api import flights, stats, airlines

# Ensure correct MIME types for frontend files
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

app.include_router(flights.router)
app.include_router(stats.router)
app.include_router(airlines.router)

@app.get("/health")
async def health():
    return {"status": "healthy"}

# --- الطريقة المضمونة لتقديم ملفات React ---
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))

if os.path.exists(frontend_dist):
    logger.info(f"Serving frontend from: {frontend_dist}")
    
    # تقديم مجلد assets (الذي يحتوي على JS و CSS) بشكل صريح
    assets_path = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    
    # تقديم أي ملفات أخرى في الجذر (مثل favicon.ico)
    @app.get("/{file_path:path}")
    async def serve_static_files(file_path: str):
        full_path = os.path.join(frontend_dist, file_path)
        if os.path.isfile(full_path):
            return FileResponse(full_path)
        # إذا لم يكن الملف موجوداً (أو كان مساراً لـ React Router)، أرسل index.html
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    logger.warning("Frontend build not found!")
    @app.get("/{catchall:path}")
    async def root():
        return {"message": "API is running, but frontend build was not found."}