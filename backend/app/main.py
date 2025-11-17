from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .api.v1 import task

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ASA MVP API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(task.router, prefix="/api/v1/task", tags=["tasks"])

@app.get("/")
def root():
    return {"message": "ASA MVP API"}

@app.get("/health")
def health():
    return {"status": "healthy"}

