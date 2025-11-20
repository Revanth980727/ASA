from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
from .api.v1 import task, enhanced, usage
from .observability import (
    setup_opentelemetry,
    instrument_fastapi,
    instrument_sqlalchemy,
    get_prometheus_metrics
)

# Set up OpenTelemetry
setup_opentelemetry(service_name="asa-backend")

# Create database tables
Base.metadata.create_all(bind=engine)

# Instrument SQLAlchemy
instrument_sqlalchemy(engine)

app = FastAPI(
    title="ASA - Automated Software Agent API",
    version="2.0.0",
    description="AI-powered automated bug fixing system"
)

# Instrument FastAPI
instrument_fastapi(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(task.router, prefix="/api/v1/task", tags=["tasks"])
app.include_router(enhanced.router, prefix="/api/v1", tags=["enhanced"])
app.include_router(usage.router, prefix="/api/v1/usage", tags=["usage"])

# Serve static frontend files (if they exist)
try:
    app.mount("/static", StaticFiles(directory="frontend/dist"), name="static")
except RuntimeError:
    pass  # Frontend not built yet

@app.get("/")
def root():
    return {"message": "ASA MVP API"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=get_prometheus_metrics(), media_type="text/plain")

