# ASA MVP - Autonomous Bug Fixer

This is the MVP project for an Autonomous Software Architect (ASA) system that can automatically fix bugs in a single repository.

## Project Structure

```
ASA/
├── backend/          # FastAPI backend
│   └── app/
│       ├── main.py   # FastAPI application
│       ├── models.py # SQLAlchemy models
│       ├── schemas.py # Pydantic schemas
│       ├── database.py # Database setup
│       └── api/
│           └── v1/
│               └── task.py # Task endpoints
├── frontend/         # React frontend
│   └── src/
│       └── App.js    # Main React component
└── README.md
```

## Backend Setup

### Prerequisites
- Python 3.8 or higher
- pip

### Installation

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
```

3. Activate the virtual environment:
   - On Windows:
   ```bash
   venv\Scripts\activate
   ```
   - On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Backend

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

API Documentation (Swagger UI) will be available at `http://localhost:8000/docs`

## Frontend Setup

### Prerequisites
- Node.js 14 or higher
- npm or yarn

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

### Running the Frontend

Start the React development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### POST /api/v1/task/submit
Submit a new bug fix task.

**Request Body:**
```json
{
  "repo_url": "https://github.com/user/repo.git",
  "bug_description": "Description of the bug"
}
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "QUEUED"
}
```

### GET /api/v1/task/{task_id}
Get details of a specific task.

**Response:**
```json
{
  "task_id": "uuid-string",
  "repo_url": "https://github.com/user/repo.git",
  "bug_description": "Description of the bug",
  "status": "QUEUED",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### GET /api/v1/task
Get a list of all tasks.

**Response:**
```json
[
  {
    "task_id": "uuid-string",
    "repo_url": "https://github.com/user/repo.git",
    "status": "QUEUED",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

## Task Status Values

- `QUEUED` - Task has been submitted and is waiting to be processed
- `CLONING_REPO` - Repository is being cloned
- `INDEXING_CODE` - Code is being indexed
- `COMPLETED` - Task completed successfully
- `FAILED` - Task failed

## Database

The backend uses SQLite with a database file `asa.db` created in the backend directory.

## Development Notes

- The backend and frontend run on separate ports (8000 and 3000)
- CORS is configured to allow requests from the React dev server
- The frontend polls the backend every 5 seconds to update task statuses
- This MVP does not yet implement the actual bug fixing logic - it only handles task submission and status tracking

