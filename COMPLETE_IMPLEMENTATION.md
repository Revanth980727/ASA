# 📘 COMPLETE IMPLEMENTATION GUIDE
## Understanding How ASA Works (Explained Simply)

---

## 📖 Table of Contents

1. [Overview - The Big Picture](#overview---the-big-picture)
2. [Project Architecture](#project-architecture)
3. [How Data Flows Through the System](#how-data-flows-through-the-system)
4. [Backend Components Explained](#backend-components-explained)
5. [Frontend Components Explained](#frontend-components-explained)
6. [The Bug-Fixing Workflow](#the-bug-fixing-workflow)
7. [Advanced Features](#advanced-features)
8. [Database Structure](#database-structure)
9. [Configuration Options](#configuration-options)
10. [Extending ASA](#extending-asa)
11. [Performance and Optimization](#performance-and-optimization)
12. [Security Considerations](#security-considerations)
13. [Troubleshooting Deep Dive](#troubleshooting-deep-dive)

---

## 🎯 Overview - The Big Picture

### What Problem Does ASA Solve?

**Problem:** Developers spend hours finding and fixing bugs manually.

**Solution:** ASA is a "robot programmer" that:
1. Reads your code automatically
2. Understands what the bug is (using AI)
3. Writes tests to verify the bug
4. Generates a fix
5. Creates a Pull Request for you to review

### How Does It Work? (Simple Version)

Think of ASA like a factory assembly line:

```
INPUT (You) → ASA Factory → OUTPUT (Fixed Code)
```

**Step-by-step:**
1. **You submit a bug** (like "login button broken")
2. **ASA clones your repo** (downloads your code)
3. **ASA reads the code** (understands the structure)
4. **ASA writes a test** (to check if login button works)
5. **ASA runs the test** (confirms the bug exists)
6. **ASA asks OpenAI** ("How do I fix this?")
7. **OpenAI suggests a fix** (AI-generated code)
8. **ASA applies the fix** (modifies your files)
9. **ASA tests again** (verifies the fix works)
10. **ASA creates a PR** (submits to GitHub for your review)

---

## 🏗️ Project Architecture

### The Two Main Parts

ASA is split into two programs that work together:

#### 1. **Backend** (The Brain) - Port 8000
- Written in **Python**
- Uses **FastAPI** framework
- Handles all the "thinking"
- Talks to OpenAI AI
- Manages the database
- Runs tests
- Creates Pull Requests

#### 2. **Frontend** (The Face) - Port 3000
- Written in **JavaScript** (React)
- The website you see and click
- Pretty forms and buttons
- Shows task progress
- Displays results

### How They Communicate

```
You → Frontend (website) → Backend (Python) → OpenAI → GitHub
                ↓              ↓
           Shows progress  Stores in database
```

**Communication Method:** HTTP requests (like when you visit a website)

---

## 📁 Project Structure (File Map)

Here's where everything lives:

```
ASA/
│
├── backend/                  # The Python "brain"
│   ├── app/
│   │   ├── main.py          # 🚪 Main entry point (starts the server)
│   │   ├── database.py      # 💾 Database connection setup
│   │   ├── models.py        # 📋 Database table definitions
│   │   ├── schemas.py       # 📝 Data validation rules
│   │   │
│   │   ├── api/             # 🌐 API endpoints (what frontend can call)
│   │   │   └── v1/
│   │   │       ├── task.py  # Task submission & status
│   │   │       └── usage.py # Usage statistics
│   │   │
│   │   ├── core/            # 🧠 Core systems
│   │   │   ├── errors.py    # Error types & retry logic
│   │   │   ├── limits.py    # Budget & rate limits
│   │   │   ├── prompt_loader.py  # Loads AI prompts
│   │   │   ├── retry_handler.py  # Automatic retries
│   │   │   └── prompts/     # AI prompt templates
│   │   │       ├── guardian_v1.json
│   │   │       ├── cit_v1.json
│   │   │       └── code_agent_v1.json
│   │   │
│   │   ├── services/        # 🔧 The workers (do the actual work)
│   │   │   ├── llm_gateway.py      # Talks to OpenAI
│   │   │   ├── code_agent.py       # Generates fixes
│   │   │   ├── test_generator.py   # Creates tests
│   │   │   ├── github_pr_manager.py # Makes Pull Requests
│   │   │   ├── docker_sandbox.py    # Runs tests safely
│   │   │   ├── queue.py            # Manages task queue
│   │   │   └── worker_tasks.py     # Background job processor
│   │   │
│   │   └── tests/           # 🧪 Automated tests
│   │       ├── unit/        # Test individual pieces
│   │       └── contract/    # Test API endpoints
│   │
│   ├── alembic/             # 📦 Database migration system
│   │   ├── versions/        # Migration history files
│   │   │   └── 338cc9f9ac27_initial_migration_with_all_models.py
│   │   ├── env.py          # Migration environment config
│   │   ├── script.py.mako  # Template for new migrations
│   │   └── README          # Alembic info
│   │
│   ├── requirements.txt     # List of Python packages needed
│   ├── alembic.ini         # Alembic configuration
│   ├── .env                 # 🔐 SECRET KEYS (don't share!)
│   └── asa.db              # 💾 Database file (SQLite)
│
├── frontend/                # The React website
│   ├── src/
│   │   ├── App.js          # Main React component
│   │   ├── App.css         # Styling
│   │   └── index.js        # Entry point
│   ├── package.json        # List of Node packages needed
│   └── node_modules/       # Downloaded packages
│
├── .github/
│   └── workflows/
│       └── test.yml        # 🤖 Automated testing (CI/CD)
│
├── README.md               # 📖 Quick start guide
└── COMPLETE_IMPLEMENTATION.md  # 📘 This file!
```

---

## 🔄 How Data Flows Through the System

### The Journey of a Bug Fix Request

Let's trace exactly what happens when you submit a bug:

#### **Step 1: You Click "Submit Task"**

```
Frontend (React)
    ↓
    Sends POST request to http://localhost:8000/api/v1/task/submit
    Body: {
        "repo_url": "https://github.com/user/repo",
        "bug_description": "Login button broken",
        "test_command": "pytest"
    }
```

#### **Step 2: Backend Receives Request**

**File:** `backend/app/api/v1/task.py`

```python
@router.post("/submit")
def submit_task(task: TaskSubmit, db: Session):
    # 1. Validate input (Pydantic does this automatically)
    # 2. Check if queue has space
    # 3. Create database record
    db_task = Task(
        repo_url=task.repo_url,
        bug_description=task.bug_description,
        status="QUEUED"
    )
    db.add(db_task)
    db.commit()

    # 4. Enqueue the task for processing
    queue.enqueue_task(run_task_job, task_id=db_task.id)

    # 5. Return task details
    return db_task
```

#### **Step 3: Task Goes into Queue**

**File:** `backend/app/services/queue.py`

The queue is like a waiting line at a store. Tasks are processed one at a time.

```
QUEUE: [Task1, Task2, Task3] → Worker picks next task
```

#### **Step 4: Background Worker Starts Processing**

**File:** `backend/app/services/worker_tasks.py`

```python
def run_task_job(task_id):
    # This runs in the background!
    # 1. Clone the repository
    # 2. Index the code
    # 3. Generate test
    # 4. Run test
    # 5. Generate fix
    # 6. Apply fix
    # 7. Test again
    # 8. Create Pull Request
```

Each step updates the database:
```
Status: QUEUED → CLONING_REPO → INDEXING → TESTING → FIXING → CREATING_PR → COMPLETED
```

#### **Step 5: Frontend Polls for Updates**

The frontend checks every 5 seconds:

```javascript
// In App.js
useEffect(() => {
    const interval = setInterval(() => {
        fetch('http://localhost:8000/api/v1/task')
            .then(response => response.json())
            .then(tasks => setTasks(tasks));
    }, 5000);  // Every 5 seconds
}, []);
```

You see the status update in real-time!

---

## 🧠 Backend Components Explained

### 1. Main Entry Point (`main.py`)

**What it does:** Starts the web server and sets up routes.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ASA - Autonomous Software Agent")

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(task_router, prefix="/api/v1/task")
app.include_router(usage_router, prefix="/api/v1/usage")
```

**Think of it as:** The receptionist at a hotel who directs you to different departments.

---

### 2. Database Layer (`database.py`, `models.py`)

#### `database.py` - Connection Manager

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create connection to SQLite database
engine = create_engine("sqlite:///./asa.db")
SessionLocal = sessionmaker(bind=engine)

# Helper function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db  # Use the database
    finally:
        db.close()  # Always close when done
```

**Think of it as:** A librarian who opens and closes books for you.

#### `models.py` - Table Definitions

```python
from sqlalchemy import Column, String, DateTime, Text

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    repo_url = Column(String, nullable=False)
    bug_description = Column(Text, nullable=False)
    status = Column(String, default="QUEUED")
    pr_url = Column(String, nullable=True)
    logs = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

**Database Table Structure:**

| Column | Type | Example |
|--------|------|---------|
| id | String | "abc-123-def-456" |
| repo_url | String | "https://github.com/user/repo" |
| bug_description | Text | "Login button doesn't work" |
| status | String | "QUEUED", "COMPLETED", etc. |
| pr_url | String | "https://github.com/user/repo/pull/42" |
| logs | Text | "Started at 10:00..." |
| created_at | DateTime | "2025-01-17 10:00:00" |
| updated_at | DateTime | "2025-01-17 10:05:23" |

**Think of it as:** An Excel spreadsheet where each row is a task.

---

### 3. LLM Gateway (`llm_gateway.py`)

**What it does:** Talks to OpenAI's API in a controlled way.

**Why we need it:** To track costs, enforce budgets, and handle errors properly.

```python
class LLMGateway:
    def __init__(self, task_id, user_id):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.task_id = task_id
        self._total_cost = 0.0

    def chat_completion(self, purpose, messages):
        # 1. Check if we're within budget
        self._check_budgets()

        # 2. Make API call to OpenAI
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2
        )

        # 3. Calculate cost
        cost = self._calculate_cost(response.usage)
        self._total_cost += cost

        # 4. Log to database
        self._log_usage(cost, response.usage)

        # 5. Return the AI's response
        return response.choices[0].message.content
```

**Features:**
- ✅ **Budget enforcement** - Stops if you spend too much
- ✅ **Automatic retries** - If OpenAI is busy, tries again
- ✅ **Cost tracking** - Knows exactly how much each call costs
- ✅ **Error handling** - Gracefully handles failures

**Example:**
```python
gateway = LLMGateway(task_id="task-123")

response = gateway.chat_completion(
    purpose=LLMPurpose.FIX_GENERATION,
    messages=[
        {"role": "system", "content": "You are a code fixer"},
        {"role": "user", "content": "Fix this bug: login button broken"}
    ]
)
# response = "The issue is in line 42..."
```

---

### 4. Prompt Loader (`prompt_loader.py`)

**What it does:** Loads pre-written prompts that tell the AI how to behave.

**Why:** Instead of writing prompts in code, we store them in JSON files. This makes them easy to update and version.

**Example Prompt File** (`guardian_v1.json`):
```json
{
  "version": "1.0.0",
  "schema_version": "v1",
  "purpose": "GUARDIAN",
  "system_prompt": "You are a security guardian. Check code for vulnerabilities.",
  "user_prompt_template": "Analyze this fix: {proposed_fix}",
  "output_schema": {
    "type": "object",
    "required": ["safe", "risk_level", "issues"],
    "properties": {
      "safe": {"type": "boolean"},
      "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
      "issues": {"type": "array"}
    }
  }
}
```

**How to use:**
```python
from app.core.prompt_loader import load_prompt

# Load the guardian prompt
prompt = load_prompt(LLMPurpose.GUARDIAN, version="v1")

# Render it with your variables
messages = prompt.get_messages(
    proposed_fix="Changed login.py line 42",
    code_context="def login(user): ..."
)

# Call OpenAI
response = llm_gateway.chat_completion_with_prompt(
    purpose=LLMPurpose.GUARDIAN,
    version="v1",
    proposed_fix="...",
    code_context="..."
)

# Automatically validated against schema!
```

---

### 5. Error Taxonomy (`errors.py`)

**What it does:** Defines all possible errors and how to handle them.

**Instead of:**
```python
raise Exception("Something went wrong")  # Bad!
```

**We do:**
```python
raise ASAError(
    ErrorType.LLM_RATE_LIMIT,
    details={"retry_after": 60}
)  # Good! Specific and actionable
```

**Error Categories:**

| Category | Should Retry? | Examples |
|----------|---------------|----------|
| **TRANSIENT** | ✅ Yes | Network timeout, rate limit |
| **PERMANENT** | ❌ No | File not found, invalid code |
| **POLICY** | ❌ No | Security violation, secret exposed |
| **USER** | ❌ No | Invalid input, missing field |
| **RESOURCE** | ❌ No | Budget exceeded, queue full |

**Example:**
```python
try:
    # Try to call OpenAI
    response = openai.chat.completions.create(...)
except RateLimitError:
    # Classify as LLM_RATE_LIMIT
    raise ASAError(
        ErrorType.LLM_RATE_LIMIT,
        details={"retry_after": 60}
    )
```

**Automatic Retries:**
```python
@with_retry(error_types=[ErrorType.LLM_RATE_LIMIT])
def call_openai():
    # If this raises LLM_RATE_LIMIT, automatically retries
    # with exponential backoff (2s, 4s, 8s, 16s...)
    pass
```

---

### 6. Queue System (`queue.py`)

**What it does:** Manages the waiting line of tasks.

**Why:** We can't process 100 bugs at once. Process them one at a time (or a few at a time).

```python
class TaskQueue:
    def __init__(self):
        self.redis = Redis()  # Fast in-memory storage
        self.queue = Queue(connection=self.redis)

    def can_enqueue(self, user_id):
        # Check limits
        queue_size = self.queue.count
        user_tasks_today = self._count_user_tasks_today(user_id)

        if queue_size >= QueueLimits.MAX_QUEUE_SIZE:
            return False, "Queue full"

        if user_tasks_today >= QueueLimits.MAX_TASKS_PER_USER_PER_DAY:
            return False, "Daily limit reached"

        return True, "OK"

    def enqueue_task(self, task_id):
        # Add to queue
        job = self.queue.enqueue(
            run_task_job,
            task_id=task_id,
            timeout='30m'  # Max 30 minutes per task
        )
        return job
```

**Queue Limits:**
- Max queue size: 100 tasks
- Max per user per day: 20 tasks
- Task timeout: 30 minutes

---

### 7. Code Agent (`code_agent.py`)

**What it does:** Generates the actual code fix using AI.

**Process:**
```python
class CodeAgent:
    def generate_fix(self, bug_description, test_failure_log, code_context):
        # 1. Load the code_agent prompt
        prompt = load_prompt(LLMPurpose.FIX_GENERATION, "v1")

        # 2. Call OpenAI
        response = self.llm_gateway.chat_completion_with_prompt(
            purpose=LLMPurpose.FIX_GENERATION,
            bug_description=bug_description,
            test_failure_log=test_failure_log,
            code_context=code_context
        )

        # 3. Response is automatically validated against schema
        # Returns:
        {
            "patches": [
                {
                    "file_path": "login.py",
                    "patch_type": "replace",
                    "start_line": 42,
                    "end_line": 45,
                    "new_code": "    return user.authenticate()",
                    "description": "Fixed authentication call"
                }
            ],
            "rationale": "The bug was caused by...",
            "confidence": 0.85
        }
```

**Patch Types:**

| Type | What It Does | Example |
|------|--------------|---------|
| `replace` | Replace lines X-Y | Replace lines 10-15 |
| `insert` | Add new lines before X | Insert before line 20 |
| `delete` | Remove lines X-Y | Delete lines 30-35 |

---

### 8. Test Generator (`test_generator.py`)

**What it does:** Creates automated tests to verify bugs.

**Example:**
```python
class TestGenerator:
    def generate_cit_test(self, bug_description, app_context):
        # Creates a Playwright E2E test
        response = self.llm_gateway.chat_completion_with_prompt(
            purpose=LLMPurpose.CIT_GENERATION,
            bug_description=bug_description,
            app_context=app_context
        )

        # Returns:
        {
            "test_code": "test('login button works', async ({ page }) => { ... })",
            "test_description": "Verifies login button click triggers authentication",
            "expected_behavior": {
                "before_fix": "fail",  # Test should fail before fix
                "after_fix": "pass"    # Test should pass after fix
            }
        }
```

**The generated test file:**
```javascript
// tests/login_button.spec.js
import { test, expect } from '@playwright/test';

test('login button works', async ({ page }) => {
    // 1. Go to login page
    await page.goto('http://localhost:3000/login');

    // 2. Click login button
    await page.click('button#login');

    // 3. Verify redirect to dashboard
    await expect(page).toHaveURL('http://localhost:3000/dashboard');
});
```

---

### 9. Docker Sandbox (`docker_sandbox.py`)

**What it does:** Runs tests in a safe container.

**Why:** We don't want tests to break your computer or access sensitive data.

```python
class DockerSandbox:
    def run_test(self, test_file_path, workspace_path):
        # 1. Create Docker container
        container = docker.run(
            image="playwright:v1.40.0",
            volumes={workspace_path: '/workspace'},
            network='none',  # No internet access
            memory='512m',   # Limit memory
            timeout=60       # Max 60 seconds
        )

        # 2. Run test inside container
        result = container.exec(['npx', 'playwright', 'test', test_file_path])

        # 3. Cleanup
        container.stop()
        container.remove()

        return result.exit_code, result.stdout, result.stderr
```

**Safety Features:**
- ❌ No internet access
- ⏰ Timeout after 60 seconds
- 💾 Limited memory (512MB)
- 🔒 Isolated filesystem
- 🧹 Auto-cleanup

---

### 10. GitHub PR Manager (`github_pr_manager.py`)

**What it does:** Creates Pull Requests on GitHub.

```python
class GitHubPRManager:
    def create_pr(self, repo_url, branch_name, title, body):
        # 1. Authenticate with GitHub
        github = Github(os.getenv("GITHUB_TOKEN"))

        # 2. Get repository
        repo = github.get_repo(repo_url)

        # 3. Create Pull Request
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,      # Your fix branch
            base="main"            # Target branch
        )

        # 4. Return PR URL
        return pr.html_url
```

**Example PR:**
- **Title:** `[ASA] Fix: Login button not working`
- **Body:**
  ```markdown
  ## Bug Description
  The login button doesn't trigger authentication.

  ## Changes
  - Fixed authentication call in login.py line 42
  - Updated event handler to use correct method

  ## Test Results
  ✅ All tests passing

  ## AI Confidence
  85%

  ---
  🤖 Generated by ASA (Autonomous Software Agent)
  ```

---

## 🖥️ Frontend Components Explained

### React App Structure

**File:** `frontend/src/App.js`

```javascript
function App() {
    // State: Data that changes
    const [tasks, setTasks] = useState([]);
    const [formData, setFormData] = useState({
        repo_url: '',
        bug_description: '',
        test_command: ''
    });

    // Effect: Run on component load
    useEffect(() => {
        fetchTasks();  // Load existing tasks
        const interval = setInterval(fetchTasks, 5000);  // Poll every 5s
        return () => clearInterval(interval);  // Cleanup
    }, []);

    // Handlers
    const handleSubmit = async (e) => {
        e.preventDefault();
        const response = await fetch('http://localhost:8000/api/v1/task/submit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        });
        const newTask = await response.json();
        setTasks([...tasks, newTask]);
    };

    const fetchTasks = async () => {
        const response = await fetch('http://localhost:8000/api/v1/task');
        const data = await response.json();
        setTasks(data);
    };

    // Render
    return (
        <div>
            <h1>ASA - Bug Fixer</h1>
            <form onSubmit={handleSubmit}>
                <input name="repo_url" onChange={e => setFormData({...formData, repo_url: e.target.value})} />
                <textarea name="bug_description" onChange={e => setFormData({...formData, bug_description: e.target.value})} />
                <input name="test_command" onChange={e => setFormData({...formData, test_command: e.target.value})} />
                <button type="submit">Submit Task</button>
            </form>

            <TaskList tasks={tasks} />
        </div>
    );
}
```

**Key Concepts:**

1. **State** - Data that can change (like tasks list)
2. **Effect** - Code that runs on load/update
3. **Handlers** - Functions that respond to clicks/changes
4. **Components** - Reusable UI pieces

---

## 🔄 The Bug-Fixing Workflow (Complete)

Let's trace a complete bug fix from start to finish:

### Phase 1: Submission ✅

**User Action:** Fills form and clicks "Submit Task"

**What Happens:**
1. Frontend validates input
2. Sends POST request to backend
3. Backend creates database record
4. Backend enqueues task
5. Returns task ID to frontend
6. Frontend shows task in list with status "QUEUED"

### Phase 2: Repository Cloning 📥

**Status:** CLONING_REPO

**What Happens:**
```python
# Clone repository to temporary workspace
workspace_path = clone_repository(task.repo_url)
# /tmp/asa/workspace_abc123/
```

**Files Created:**
- `/tmp/asa/workspace_abc123/` - Full repo clone

### Phase 3: Code Indexing 📚

**Status:** INDEXING_CODE

**What Happens:**
```python
# Read all source files
# Build code index (file tree, imports, functions)
code_index = index_codebase(workspace_path)
```

**Index Contains:**
- File list
- Function definitions
- Class structure
- Import dependencies

### Phase 4: Test Generation 🧪

**Status:** GENERATING_TEST

**What Happens:**
```python
# Ask AI to create test
test_code = test_generator.generate_cit_test(
    bug_description="Login button doesn't work",
    app_context=code_index
)

# Save test file
save_test_file(test_code, path="tests/login_test.spec.js")
```

**Test File Created:**
```javascript
test('login button works', async ({ page }) => {
    await page.goto('http://localhost:3000/login');
    await page.click('#login-button');
    await expect(page).toHaveURL('/dashboard');
});
```

### Phase 5: Pre-Fix Testing ❌

**Status:** TESTING_BEFORE_FIX

**What Happens:**
```python
# Run test in Docker
result = docker_sandbox.run_test('tests/login_test.spec.js')
# Expected: FAIL (bug exists)

if result.exit_code != 0:
    test_failure_log = result.stderr
    # Good! Test confirms the bug
else:
    # Uh oh, test passed but shouldn't have
    mark_task_failed("Test passed when bug should exist")
```

### Phase 6: Fix Generation 🔧

**Status:** GENERATING_FIX

**What Happens:**
```python
# Ask AI to generate fix
fix_response = code_agent.generate_fix(
    bug_description="Login button doesn't work",
    test_failure_log=test_failure_log,
    code_context=get_relevant_code(code_index, "login")
)

# Returns:
{
    "patches": [{
        "file_path": "src/Login.js",
        "patch_type": "replace",
        "start_line": 42,
        "end_line": 44,
        "new_code": "  const handleLogin = () => authenticate(user);",
        "description": "Fixed event handler"
    }],
    "confidence": 0.87
}
```

### Phase 7: Security Check 🛡️

**Status:** VALIDATING_SECURITY

**What Happens:**
```python
# Ask AI guardian to check fix
guardian_response = guardian_agent.validate_fix(
    proposed_fix=fix_response,
    code_context=code_context
)

if not guardian_response['safe']:
    mark_task_failed("Security violation detected")
    return

# Good to go!
```

### Phase 8: Apply Fix ✏️

**Status:** APPLYING_FIX

**What Happens:**
```python
# Apply each patch
for patch in fix_response['patches']:
    apply_patch(
        file_path=patch['file_path'],
        start_line=patch['start_line'],
        end_line=patch['end_line'],
        new_code=patch['new_code']
    )

# Commit changes
git.add('.')
git.commit('-m', '[ASA] Fix: Login button not working')
```

### Phase 9: Post-Fix Testing ✅

**Status:** TESTING_AFTER_FIX

**What Happens:**
```python
# Run test again
result = docker_sandbox.run_test('tests/login_test.spec.js')

if result.exit_code == 0:
    # Success! Test passes now
    pass
else:
    # Fix didn't work
    mark_task_failed("Fix didn't resolve the bug")
    return
```

### Phase 10: Create Pull Request 🚀

**Status:** CREATING_PR

**What Happens:**
```python
# Push branch to GitHub
git.push('origin', branch_name)

# Create PR
pr_url = github_pr_manager.create_pr(
    repo_url=task.repo_url,
    branch_name=branch_name,
    title=f"[ASA] Fix: {task.bug_description}",
    body=generate_pr_body(fix_response, test_results)
)

# Update task
task.pr_url = pr_url
task.status = "COMPLETED"
db.commit()
```

### Phase 11: Completion 🎉

**Status:** COMPLETED

**User Sees:**
- ✅ Status: COMPLETED
- 🔗 PR Link: Click to view on GitHub
- 📊 Logs: Full execution log
- 💰 Cost: How much OpenAI charged

---

## ⚙️ Configuration Options

### Environment Variables (`.env`)

| Variable | What It Does | Example |
|----------|--------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-abc123...` |
| `GITHUB_TOKEN` | Your GitHub access token | `ghp_xyz789...` |
| `DATABASE_URL` | Database connection | `sqlite:///./asa.db` |
| `DEFAULT_MODEL` | Which AI model to use | `gpt-4o-mini` |
| `MAX_COST_PER_TASK` | Budget limit per task | `5.0` (dollars) |
| `MAX_QUEUE_SIZE` | Max pending tasks | `100` |
| `ENABLE_OPENTELEMETRY` | Detailed logging | `false` |

### Budget Limits (`backend/app/core/limits.py`)

```python
class BudgetLimits:
    MAX_TOKENS_PER_TASK = 100000          # ~100k tokens per task
    MAX_COST_PER_TASK_USD = 5.0           # $5 max per task
    MAX_COST_PER_USER_PER_DAY_USD = 50.0  # $50 max per user per day

class QueueLimits:
    MAX_QUEUE_SIZE = 100                  # 100 tasks max in queue
    MAX_TASKS_PER_USER_PER_DAY = 20       # 20 tasks per user per day
```

### Model Configuration

```python
# Cheaper, faster (recommended for testing)
DEFAULT_MODEL = "gpt-4o-mini"
# Cost: $0.15 per 1M input tokens, $0.60 per 1M output tokens

# Smarter, more expensive
# DEFAULT_MODEL = "gpt-4o"
# Cost: $2.50 per 1M input tokens, $10 per 1M output tokens
```

---

## 🗄️ Database Structure

### Database Migration System (Alembic)

**What is Alembic?** A database migration tool that tracks and applies changes to your database schema safely.

**Why do we need it?** When you modify `models.py` (add new tables, columns, or change existing ones), the database needs to be updated. Alembic:
- ✅ Tracks all database changes over time
- ✅ Applies changes without losing data
- ✅ Allows rollback if something goes wrong
- ✅ Keeps database structure in sync with code

**How it works:**
```
Code Changes → Create Migration → Apply Migration → Database Updated
```

#### Alembic Files

**`alembic.ini`** - Configuration file
```ini
[alembic]
script_location = alembic         # Where migrations live
sqlalchemy.url = sqlite:///./asa.db  # Database connection
```

**`alembic/env.py`** - Migration environment
```python
from app.database import Base
from app import models  # Import all models

target_metadata = Base.metadata  # What Alembic should track
```

**`alembic/versions/`** - Migration history
Each file represents one database change:
```python
# 338cc9f9ac27_initial_migration_with_all_models.py
def upgrade() -> None:
    # Create tables
    op.create_table('tasks', ...)
    op.create_table('llm_usage', ...)

def downgrade() -> None:
    # Rollback (reverse the changes)
    op.drop_table('llm_usage')
    op.drop_table('tasks')
```

#### Common Alembic Commands

| Command | What It Does |
|---------|--------------|
| `alembic current` | Show current migration version |
| `alembic history` | Show all migration history |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Rollback last migration |
| `alembic revision --autogenerate -m "msg"` | Create new migration |

#### Creating a New Migration

**Example:** You add a new column to the Task model:

```python
# In models.py
class Task(Base):
    __tablename__ = "tasks"
    # ... existing columns ...
    priority = Column(String, nullable=True)  # NEW COLUMN
```

**Steps:**
1. **Generate migration:**
```bash
cd backend
python -m alembic revision --autogenerate -m "Add priority column to tasks"
```

Alembic creates a new file in `alembic/versions/`:
```python
# abc123_add_priority_column_to_tasks.py
def upgrade() -> None:
    op.add_column('tasks', sa.Column('priority', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('tasks', 'priority')
```

2. **Review the migration** (make sure it looks correct)

3. **Apply the migration:**
```bash
python -m alembic upgrade head
```

4. **Done!** Your database now has the new column.

#### Important Notes

**⚠️ Reserved Word Conflict:** SQLAlchemy reserves the word `metadata` for its internal use. That's why in our models, we use:
- `PromptVersion.meta_data` (not `metadata`)
- `EvaluationCase.extra_metadata` (not `metadata`)

If you use `metadata` as a column name, you'll get this error:
```
Attribute name 'metadata' is reserved when using the Declarative API
```

**Migration Best Practices:**
- Always review auto-generated migrations before applying
- Test migrations on development database first
- Never edit applied migrations (create a new one instead)
- Commit migration files to git

---

### Tables

#### 1. `tasks` Table
Stores all bug fix tasks.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Unique task ID (UUID) |
| repo_url | VARCHAR | GitHub repository URL |
| bug_description | TEXT | What's broken |
| test_command | VARCHAR | How to run tests |
| status | VARCHAR | Current status |
| workspace_path | VARCHAR | Where code is cloned |
| branch_name | VARCHAR | Git branch name |
| pr_url | VARCHAR | Pull Request URL |
| logs | TEXT | Execution logs |
| e2e_test_path | VARCHAR | Path to generated test |
| job_id | VARCHAR | Background job ID |
| user_id | VARCHAR | Who submitted it |
| created_at | DATETIME | When created |
| updated_at | DATETIME | Last update |

#### 2. `llm_usage` Table
Tracks every AI API call.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Unique ID |
| task_id | VARCHAR | Related task |
| user_id | VARCHAR | Who triggered it |
| model | VARCHAR | AI model used |
| prompt_tokens | INTEGER | Input tokens |
| completion_tokens | INTEGER | Output tokens |
| total_tokens | INTEGER | Total tokens |
| cost_usd | FLOAT | Cost in dollars |
| latency_ms | FLOAT | How long it took |
| status | VARCHAR | success/error |
| error_message | TEXT | Error details |
| timestamp | DATETIME | When it happened |

#### 3. `task_metrics` Table
Performance metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Unique ID |
| task_id | VARCHAR | Related task |
| metric_name | VARCHAR | What metric |
| metric_value | FLOAT | Value |
| timestamp | DATETIME | When measured |

#### 4. `prompt_versions` Table
Stores versioned AI prompts with checksums.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Unique ID |
| name | VARCHAR | Prompt name (indexed) |
| version | VARCHAR | Version string (indexed) |
| template | TEXT | Prompt template |
| variables | TEXT | JSON array of variables |
| checksum | VARCHAR | Hash for verification |
| meta_data | TEXT | JSON metadata (Note: renamed from 'metadata' due to SQLAlchemy reserved word) |
| created_at | DATETIME | When created (indexed) |

#### 5. `feedback` Table
User feedback on task execution for RLHF (Reinforcement Learning from Human Feedback).

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Unique ID |
| task_id | VARCHAR | Related task (indexed) |
| user_id | VARCHAR | Who gave feedback (indexed) |
| rating | INTEGER | Rating 1-5 scale |
| approved | BOOLEAN | Whether fix was approved |
| comment | TEXT | User comments |
| issues | TEXT | JSON array of issues found |
| feedback_type | VARCHAR | 'user' or 'auto' |
| created_at | DATETIME | When created (indexed) |

#### 6. `evaluation_cases` Table
Golden set of test cases for evaluation framework.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Unique ID |
| name | VARCHAR | Case name (unique, indexed) |
| repo_url | VARCHAR | Repository URL |
| bug_description | TEXT | Bug description |
| test_command | VARCHAR | How to run tests |
| expected_behavior | TEXT | What fix should achieve |
| difficulty | VARCHAR | easy/medium/hard |
| category | VARCHAR | Bug type: logic/syntax/integration |
| extra_metadata | TEXT | JSON for extra info (Note: renamed from 'metadata' due to SQLAlchemy reserved word) |
| is_active | BOOLEAN | Whether case is active |
| created_at | DATETIME | When created |

#### 7. `evaluation_results` Table
Results from running evaluation cases.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR | Unique ID |
| evaluation_case_id | VARCHAR | Related case (indexed) |
| task_id | VARCHAR | Related task (indexed) |
| passed | BOOLEAN | Whether test passed |
| execution_time_seconds | FLOAT | How long it took |
| cost_usd | FLOAT | OpenAI cost |
| reviewer_notes | TEXT | Human reviewer notes |
| metrics | TEXT | JSON: correctness, quality, etc. |
| created_at | DATETIME | When created (indexed) |

**Note on Reserved Words:** SQLAlchemy reserves `metadata` as an attribute name for its internal metadata tracking system. That's why `PromptVersion` uses `meta_data` and `EvaluationCase` uses `extra_metadata` instead.

---

## 🚀 Advanced Features

### 1. Automatic Retries with Exponential Backoff

When OpenAI is busy or network is slow:

```python
@with_retry(error_types=[ErrorType.LLM_RATE_LIMIT])
def call_openai():
    # Retry schedule:
    # Attempt 1: Immediate
    # Attempt 2: Wait 10 seconds
    # Attempt 3: Wait 20 seconds
    # Attempt 4: Wait 40 seconds
    # Attempt 5: Wait 60 seconds (max)
    pass
```

### 2. Prompt Versioning

Change prompts without breaking old tasks:

```
prompts/
├── guardian_v1.json   # Old version
├── guardian_v2.json   # New version with improvements
```

Old tasks use v1, new tasks use v2. No conflicts!

### 3. Schema Validation

AI responses are automatically validated:

```python
# AI responds with:
{
    "safe": true,
    "risk_level": "low"
    # Missing "issues" field!
}

# Automatic validation catches it:
# ValueError: Response missing required field: issues
```

### 4. Cost Tracking

Every AI call is logged with exact cost:

```sql
SELECT
    task_id,
    SUM(cost_usd) as total_cost,
    SUM(total_tokens) as total_tokens
FROM llm_usage
GROUP BY task_id;
```

### 5. Queue Backpressure

Prevents overload:

```python
if queue.count >= 100:
    return 429, "Queue full, try again later"

if user_tasks_today >= 20:
    return 429, "Daily limit reached"
```

---

## 🔒 Security Considerations

### 1. Never Commit `.env` File

```gitignore
# .gitignore
.env
*.db
__pycache__/
node_modules/
```

### 2. API Key Rotation

Change your keys regularly:
1. Create new key on OpenAI
2. Update `.env`
3. Restart backend
4. Delete old key

### 3. GitHub Token Permissions

Only give minimum required:
- ✅ `repo` (to read/write code)
- ✅ `workflow` (to run CI)
- ❌ Don't give `admin` or `delete_repo`!

### 4. Input Validation

All user input is validated:

```python
class TaskSubmit(BaseModel):
    repo_url: str = Field(..., min_length=1, max_length=500)
    bug_description: str = Field(..., min_length=10, max_length=5000)
    test_command: Optional[str] = Field(None, max_length=200)

    @field_validator('repo_url')
    def validate_url(cls, v):
        if not v.startswith('https://github.com/'):
            raise ValueError('Must be GitHub URL')
        return v
```

### 5. Docker Sandbox Isolation

Tests run in isolated containers:
- ❌ No internet access
- 💾 Limited memory
- ⏰ Timeout enforced
- 🔒 Can't access host system

---

## 🐛 Troubleshooting Deep Dive

### Debug Mode

Enable detailed logging:

```bash
# In .env
ENABLE_OPENTELEMETRY=true
LOG_LEVEL=DEBUG
```

### Check Logs

**Backend logs:**
```bash
# In terminal where uvicorn is running
# Look for lines like:
[INFO] Task abc-123: Status changed to CLONING_REPO
[ERROR] OpenAI API error: Rate limit exceeded
```

**Frontend logs:**
```bash
# In browser console (F12)
# Look for:
Console → Network tab → See all API calls
```

### Database Queries

```bash
# Connect to database
sqlite3 backend/asa.db

# Check task status
SELECT id, status, updated_at FROM tasks ORDER BY created_at DESC LIMIT 10;

# Check costs
SELECT task_id, SUM(cost_usd) as cost FROM llm_usage GROUP BY task_id;

# Exit
.quit
```

### Common Issues

**Issue:** Task stuck in QUEUED

**Cause:** Worker not running

**Fix:**
```bash
# Check if worker is running
ps aux | grep worker

# Start worker manually (for testing)
cd backend
python -m app.services.worker_tasks
```

---

**Issue:** "OpenAI API error: Invalid API key"

**Cause:** Wrong key in `.env`

**Fix:**
```bash
# Check .env
cat backend/.env | grep OPENAI_API_KEY

# Should start with sk-
# No spaces around =
# OPENAI_API_KEY=sk-abc123...
```

---

**Issue:** Frontend can't connect to backend

**Cause:** CORS issue or backend not running

**Fix:**
```python
# In backend/app/main.py, check:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # ← Must match frontend
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🎓 Extending ASA

### Add a New AI Agent

**Example:** Create a "Documentation Generator"

1. **Create prompt file:**
```json
// backend/app/core/prompts/doc_generator_v1.json
{
  "version": "1.0.0",
  "schema_version": "v1",
  "purpose": "DOC_GENERATION",
  "system_prompt": "You are a documentation writer...",
  "user_prompt_template": "Generate docs for: {code}",
  "output_schema": {
    "type": "object",
    "required": ["documentation", "examples"],
    "properties": {
      "documentation": {"type": "string"},
      "examples": {"type": "array"}
    }
  }
}
```

2. **Add purpose to limits:**
```python
# backend/app/core/limits.py
class LLMPurpose(str, Enum):
    GUARDIAN = "guardian"
    FIX_GENERATION = "fix_generation"
    CIT_GENERATION = "cit_generation"
    DOC_GENERATION = "doc_generation"  # ← Add this
```

3. **Create agent:**
```python
# backend/app/services/doc_generator.py
class DocGenerator:
    def __init__(self, task_id):
        self.llm_gateway = LLMGateway(task_id=task_id)

    def generate_docs(self, code):
        response = self.llm_gateway.chat_completion_with_prompt(
            purpose=LLMPurpose.DOC_GENERATION,
            version="v1",
            code=code
        )
        return response
```

4. **Add to workflow:**
```python
# In worker_tasks.py
def run_task_job(task_id):
    # ... existing steps ...

    # Add documentation step
    doc_gen = DocGenerator(task_id)
    docs = doc_gen.generate_docs(code)
    save_docs(docs)
```

### Add a New API Endpoint

```python
# backend/app/api/v1/docs.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/generate")
def generate_docs(file_path: str):
    # Read file
    code = read_file(file_path)

    # Generate docs
    doc_gen = DocGenerator()
    docs = doc_gen.generate_docs(code)

    return {"documentation": docs}
```

```python
# backend/app/main.py
from app.api.v1 import docs

app.include_router(docs.router, prefix="/api/v1/docs", tags=["docs"])
```

### Add a New Database Model

**Example:** Add a "CodeReview" model to track AI code reviews

**Step 1: Update models.py**

```python
# backend/app/models.py
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean

class CodeReview(Base):
    __tablename__ = "code_reviews"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=False, index=True)
    file_path = Column(String, nullable=False)
    review_type = Column(String, nullable=False)  # security, performance, style
    severity = Column(String, nullable=False)  # low, medium, high, critical
    line_number = Column(Integer, nullable=True)
    issue_description = Column(Text, nullable=False)
    suggestion = Column(Text, nullable=True)
    auto_fixable = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**⚠️ Important:** Avoid using `metadata` as a column name! Use `meta_data` or `extra_metadata` instead.

**Step 2: Create migration**

```bash
cd backend

# Auto-generate migration from model changes
python -m alembic revision --autogenerate -m "Add code_reviews table"

# Output:
# Generating alembic/versions/xyz123_add_code_reviews_table.py ... done
# INFO  [alembic.autogenerate.compare] Detected added table 'code_reviews'
```

**Step 3: Review the generated migration**

```python
# alembic/versions/xyz123_add_code_reviews_table.py
def upgrade() -> None:
    op.create_table('code_reviews',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('review_type', sa.String(), nullable=False),
        # ... other columns ...
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_code_reviews_task_id'), 'code_reviews', ['task_id'])

def downgrade() -> None:
    op.drop_index(op.f('ix_code_reviews_task_id'), table_name='code_reviews')
    op.drop_table('code_reviews')
```

**Step 4: Apply migration**

```bash
python -m alembic upgrade head

# Output:
# INFO  [alembic.runtime.migration] Running upgrade abc123 -> xyz123, Add code_reviews table
```

**Step 5: Verify**

```bash
python -m alembic current
# Output: xyz123 (head)

# Check in database
sqlite3 asa.db
> .schema code_reviews
> .quit
```

**Step 6: Add Pydantic schema**

```python
# backend/app/schemas.py
class CodeReview(BaseModel):
    id: str
    task_id: str
    file_path: str
    review_type: str
    severity: str
    issue_description: str
    suggestion: Optional[str] = None
    auto_fixable: bool
    created_at: datetime
```

**Step 7: Use in your code**

```python
# Create a review
from app.models import CodeReview
from app.database import SessionLocal

db = SessionLocal()
review = CodeReview(
    task_id="task-123",
    file_path="login.py",
    review_type="security",
    severity="high",
    issue_description="SQL injection vulnerability",
    suggestion="Use parameterized queries",
    auto_fixable=True
)
db.add(review)
db.commit()
```

**Migration Workflow Summary:**

```
1. Edit models.py (add/modify model)
   ↓
2. alembic revision --autogenerate -m "Description"
   ↓
3. Review generated migration file
   ↓
4. alembic upgrade head
   ↓
5. Commit migration file to git
   ✅ Done!
```

---

## 📊 Performance and Optimization

### Reduce Costs

1. **Use smaller model:**
```python
# In .env
DEFAULT_MODEL=gpt-4o-mini  # Cheaper!
# Instead of gpt-4o
```

2. **Reduce context size:**
```python
# Only send relevant code, not entire repo
relevant_code = extract_relevant_files(bug_description, code_index)
```

3. **Cache common responses:**
```python
# If same bug seen before, use cached fix
cache_key = hash(bug_description + code_context)
if cache_key in cache:
    return cache[cache_key]
```

### Speed Up Processing

1. **Parallel test execution:**
```python
# Run tests concurrently
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(run_test, test1),
        executor.submit(run_test, test2),
        executor.submit(run_test, test3)
    ]
```

2. **Async/await:**
```python
async def process_task(task_id):
    # Non-blocking operations
    code = await fetch_code(repo_url)
    test = await generate_test(code)
    result = await run_test(test)
```

3. **Database indexing:**
```sql
CREATE INDEX idx_task_status ON tasks(status);
CREATE INDEX idx_task_user ON tasks(user_id, created_at);
```

---

## 🎯 Summary

You now understand:
- ✅ How ASA's architecture works (backend + frontend)
- ✅ How data flows through the system
- ✅ What each component does
- ✅ How the bug-fixing workflow operates
- ✅ Database structure and migration system (Alembic)
- ✅ How to configure and extend ASA
- ✅ How to add new models and create migrations
- ✅ How to troubleshoot issues
- ✅ Security best practices

**Next Steps:**
1. Try running ASA on a real bug
2. Experiment with different prompts
3. Add your own custom agents
4. Monitor costs and optimize

**Remember:**
- Always keep `.env` file secret
- Monitor your OpenAI costs
- Test changes in development first
- Read error messages carefully

---

*Made with ❤️ to help you understand complex systems simply*
