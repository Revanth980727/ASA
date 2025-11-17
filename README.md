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
│       ├── services/ # Service modules
│       │   └── orchestrator.py # Task orchestrator
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
Submit a new bug fix task. The task will be queued and processed asynchronously by the TaskOrchestrator.

**Request Body:**
```json
{
  "repo_url": "https://github.com/user/repo.git",
  "bug_description": "Description of the bug",
  "test_command": "pytest"
}
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "repo_url": "https://github.com/user/repo.git",
  "bug_description": "Description of the bug",
  "test_command": "pytest",
  "status": "QUEUED",
  "workspace_path": null,
  "branch_name": null,
  "pr_url": null,
  "logs": "",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### GET /api/v1/task/{task_id}
Get details of a specific task, including current status and logs.

**Response:**
```json
{
  "task_id": "uuid-string",
  "repo_url": "https://github.com/user/repo.git",
  "bug_description": "Description of the bug",
  "test_command": "pytest",
  "status": "CLONING_REPO",
  "workspace_path": null,
  "branch_name": null,
  "pr_url": null,
  "logs": "[2024-01-01T00:00:00] Moved to CLONING_REPO",
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
    "status": "COMPLETED",
    "pr_url": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

## Task Orchestrator

The `TaskOrchestrator` is a background service that processes tasks asynchronously. When a task is submitted via the API, it is automatically queued and processed by the orchestrator.

### Current Implementation (v0)

The orchestrator currently simulates the bug-fixing workflow with the following states:

1. **QUEUED** - Task has been submitted and is waiting to be processed
2. **CLONING_REPO** - Repository is being cloned (simulated with 2-second delay)
3. **INDEXING_CODE** - Code is being indexed (simulated with 2-second delay)
4. **COMPLETED** - Task completed successfully

The orchestrator:
- Runs in a background task using FastAPI's `BackgroundTasks`
- Uses its own database session to safely update task status outside the request scope
- Appends log entries to the task's `logs` field as it progresses through states
- Updates the `updated_at` timestamp on each state change

### Future Enhancements

The orchestrator is designed to be extended with real implementations for:
- Repository cloning via `repo_manager`
- Code indexing via `code_index`
- Test generation and execution
- Bug fix generation and application
- Pull request creation

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
- Tasks are processed asynchronously in the background after submission
- The orchestrator v0 simulates state transitions with delays for testing purposes
