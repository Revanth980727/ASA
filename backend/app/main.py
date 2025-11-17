from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
from .api.v1 import task, enhanced

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ASA - Automated Software Agent API",
    version="2.0.0",
    description="AI-powered automated bug fixing system"
)

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

