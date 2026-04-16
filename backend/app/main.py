"""Main FastAPI application."""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import time
import os
import mimetypes

# Ensure correct MIME types
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')

from app.config import settings
from app.api import flights, stats, airlines

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

# --- API Routers ---
app.include_router(flights.router)
app.include_router(stats.router)
app.include_router(airlines.router)

@app.get("/health")
async def health():
    return {"status": "healthy"}

# --- تقديم ملفات React بطريقة صارمة جداً ---
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))

if os.path.exists(frontend_dist):
    logger.info(f"Serving frontend from: {frontend_dist}")
    
    # 1. تقديم مجلد assets (JS, CSS, Images)
    assets_path = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    
    # 2. تقديم الملفات في الجذر التي تحتوي على امتداد (مثل favicon.ico)
    @app.get("/{file_name}.{ext}")
    async def serve_root_files(file_name: str, ext: str):
        file_path = os.path.join(frontend_dist, f"{file_name}.{ext}")
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        raise HTTPException(status_code=404, detail="File not found")

    # 3. أي مسار آخر (بدون امتداد) يتم توجيهه إلى index.html ليعمل React
    @app.get("/{catchall:path}")
    async def serve_react_app(catchall: str):
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="index.html not found")
else:
    logger.warning("Frontend build not found!")
    @app.get("/{catchall:path}")
    async def root():
        return {"message": "API is running, but frontend build was not found."}