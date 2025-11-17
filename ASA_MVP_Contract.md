<<<<<<< HEAD
# ASA_MVP_Contract

## 1. Purpose

The ASA MVP is an **autonomous bug fixing system for a single repo**.

Given:
- A Git repository URL
- A human written bug description

It will:
1. Clone and index the repo
2. Generate a failing test that reproduces the bug
3. Generate and apply a code fix
4. Re run tests
5. Open a pull request with the fix and tests

If it cannot do this, it should fail clearly and log why.

No feature design. No multi repo work. No infra changes.

---

## 2. Scope

### In scope

- **Single repo only**
  - One task = one target repo URL
  - Assumes repo builds and tests locally with standard commands

- **Input**
  - `repo_url` (Git URL)
  - `bug_description` (free text from user)

- **Core flow**
  1. Accept task via API
  2. Clone repo into a workspace
  3. Index code (AST + embeddings or other light analysis)
  4. Use the index to find relevant files for the bug
  5. Generate a failing test that shows the bug
  6. Generate a patch for the code
  7. Apply patch and re run tests
  8. If tests pass, create a PR branch and open a PR
  9. Expose task status and logs through the API

- **Types of code changes allowed**
  - New or edited test files
  - Localized code changes (functions, classes, small helpers)
  - Config tweaks inside the same repo if needed for tests to run

---

## 3. Out of scope (for this MVP)

- No integration with JIRA, Linear, or other ticket tools
- No multi repo reasoning or cross service changes
- No infrastructure as code updates
- No cloud or deployment changes
- No high level architecture planning
- No long running background scheduler beyond what is needed to finish one task
- No full knowledge graph of the codebase, only light indexing

These can be future versions. For now, keep the system narrow and predictable.

---

## 4. System components

### 4.1 API Service (FastAPI)

Main role: entry and control plane.

Endpoints (MVP):

- `POST /api/v1/task/submit`
  - Body:
    - `repo_url: string`
    - `bug_description: string`
  - Returns:
    - `task_id`
    - initial status

- `GET /api/v1/task/{task_id}`
  - Returns:
    - current status
    - high level logs
    - link to PR if created

- `GET /api/v1/task`
  - Optional list endpoint for all tasks (for simple dashboard)

The API should not do heavy work itself. It should hand off to worker logic.

---

### 4.2 Task Orchestrator

Main role: run the state machine for a task.

High level states:

1. `QUEUED`
2. `CLONING_REPO`
3. `INDEXING_CODE`
4. `GENERATING_TEST`
5. `RUNNING_TESTS_BEFORE_FIX`
6. `GENERATING_FIX`
7. `APPLYING_FIX`
8. `RUNNING_TESTS_AFTER_FIX`
9. `OPENING_PR`
10. `COMPLETED` or `FAILED`

Each step:
- Has clear input and output
- Writes logs to storage
- Fails fast on errors and stops further steps

---

### 4.3 Repo Manager

Main role: handle git and workspace operations.

Responsibilities:

- Clone repo into a workspace folder like `workspaces/{task_id}`
- Checkout base branch (default main)
- Create fix branch, for example `asa/fix/{task_id}`
- Commit changes
- Push branch
- Call Git provider API or use CLI to open PR

---

### 4.4 Code Indexer (Guardian)

Main role: map the bug description to relevant files.

MVP behavior:

- Walk source tree (for now you can start with one language, eg TypeScript or Python)
- Build a simple code index:
  - File path
  - Top level symbols (functions, classes)
  - Short summaries (LLM, optional)
- Optionally store embeddings in a local vector store
- Expose a function:

  ```python
  search_relevant_code(bug_description) -> list[CodeSnippet]
Where CodeSnippet might be:

file path

line range

snippet text

This index does not need to be perfect. It just has to be good enough so the LLM has focused context.

4.5 Test Generator

Main role: produce a failing test that proves the bug.

Behavior:

Input:

bug_description

relevant code snippets

Output:

one or more test files written into the repo, for example:

tests/test_bug_<task_id>.py or tests/asa/test_bug_<task_id>.ts

Steps:

Decide test framework (for MVP, pick one per stack, eg pytest or Playwright)

Call LLM with:

bug description

code context

existing tests (if any) in that area

Write the returned test code into the repo

Run tests and capture results

If no test can be generated, mark task as failed with a clear reason.

4.6 Test Runner

Main role: run tests and collect results.

Runs a fixed command, for example:

npm test, or

pytest, or

a command passed in config

Runs inside a Docker container or controlled environment

Captures:

exit code

stdout and stderr

test report paths if available

Returns a structured result object that the orchestrator can use.

4.7 Code Fix Agent

Main role: generate and apply a patch.

Input:

failing test output

bug description

relevant code snippets

repo file tree

Output:

one or more patches:

file path

line range or anchor

new code block

Steps:

Ask LLM for a patch in a strict format

Validate the patch:

does file exist

does it apply cleanly

Apply patch to the workspace

Run tests again

If tests pass, ready for PR. If not, stop after one or two attempts in MVP.

4.8 PR Creator

Main role: open the pull request once tests pass.

Behavior:

Create a branch name

Commit the changes

Push to remote

Open PR with:

title: simple and clear, for example Fix bug: <short summary>

body:

bug description

what code changed

which tests were added or updated

test results summary

Return PR URL to the API and store it with the task.

5. Data model (simple version)

You can start with a minimal schema:

Task

id

repo_url

bug_description

status (enum of the states above)

created_at

updated_at

workspace_path

branch_name

pr_url

logs (text or separate log table)

6. Constraints and defaults

Assume the repo is public or reachable from the worker

Assume a single test command per repo, stored in config

Limit:

maximum repo size (eg do not index node_modules)

maximum LLM context length, so use the index to narrow input

Hard stop after a small number of fix attempts per task

7. Success criteria for this MVP

A task is considered successful if:

The system cloned the repo

It generated a test that fails before the fix

It generated a patch that made the test pass

It opened a PR with both test and code changes

Your first goal is to get this working on one real repo end to end.
=======
# ASA_MVP_Contract

## 1. Purpose

The ASA MVP is an **autonomous bug fixing system for a single repo**.

Given:
- A Git repository URL
- A human written bug description

It will:
1. Clone and index the repo
2. Generate a failing test that reproduces the bug
3. Generate and apply a code fix
4. Re run tests
5. Open a pull request with the fix and tests

If it cannot do this, it should fail clearly and log why.

No feature design. No multi repo work. No infra changes.

---

## 2. Scope

### In scope

- **Single repo only**
  - One task = one target repo URL
  - Assumes repo builds and tests locally with standard commands

- **Input**
  - `repo_url` (Git URL)
  - `bug_description` (free text from user)

- **Core flow**
  1. Accept task via API
  2. Clone repo into a workspace
  3. Index code (AST + embeddings or other light analysis)
  4. Use the index to find relevant files for the bug
  5. Generate a failing test that shows the bug
  6. Generate a patch for the code
  7. Apply patch and re run tests
  8. If tests pass, create a PR branch and open a PR
  9. Expose task status and logs through the API

- **Types of code changes allowed**
  - New or edited test files
  - Localized code changes (functions, classes, small helpers)
  - Config tweaks inside the same repo if needed for tests to run

---

## 3. Out of scope (for this MVP)

- No integration with JIRA, Linear, or other ticket tools
- No multi repo reasoning or cross service changes
- No infrastructure as code updates
- No cloud or deployment changes
- No high level architecture planning
- No long running background scheduler beyond what is needed to finish one task
- No full knowledge graph of the codebase, only light indexing

These can be future versions. For now, keep the system narrow and predictable.

---

## 4. System components

### 4.1 API Service (FastAPI)

Main role: entry and control plane.

Endpoints (MVP):

- `POST /api/v1/task/submit`
  - Body:
    - `repo_url: string`
    - `bug_description: string`
  - Returns:
    - `task_id`
    - initial status

- `GET /api/v1/task/{task_id}`
  - Returns:
    - current status
    - high level logs
    - link to PR if created

- `GET /api/v1/task`
  - Optional list endpoint for all tasks (for simple dashboard)

The API should not do heavy work itself. It should hand off to worker logic.

---

### 4.2 Task Orchestrator

Main role: run the state machine for a task.

High level states:

1. `QUEUED`
2. `CLONING_REPO`
3. `INDEXING_CODE`
4. `GENERATING_TEST`
5. `RUNNING_TESTS_BEFORE_FIX`
6. `GENERATING_FIX`
7. `APPLYING_FIX`
8. `RUNNING_TESTS_AFTER_FIX`
9. `OPENING_PR`
10. `COMPLETED` or `FAILED`

Each step:
- Has clear input and output
- Writes logs to storage
- Fails fast on errors and stops further steps

---

### 4.3 Repo Manager

Main role: handle git and workspace operations.

Responsibilities:

- Clone repo into a workspace folder like `workspaces/{task_id}`
- Checkout base branch (default main)
- Create fix branch, for example `asa/fix/{task_id}`
- Commit changes
- Push branch
- Call Git provider API or use CLI to open PR

---

### 4.4 Code Indexer (Guardian)

Main role: map the bug description to relevant files.

MVP behavior:

- Walk source tree (for now you can start with one language, eg TypeScript or Python)
- Build a simple code index:
  - File path
  - Top level symbols (functions, classes)
  - Short summaries (LLM, optional)
- Optionally store embeddings in a local vector store
- Expose a function:

  ```python
  search_relevant_code(bug_description) -> list[CodeSnippet]
Where CodeSnippet might be:

file path

line range

snippet text

This index does not need to be perfect. It just has to be good enough so the LLM has focused context.

4.5 Test Generator

Main role: produce a failing test that proves the bug.

Behavior:

Input:

bug_description

relevant code snippets

Output:

one or more test files written into the repo, for example:

tests/test_bug_<task_id>.py or tests/asa/test_bug_<task_id>.ts

Steps:

Decide test framework (for MVP, pick one per stack, eg pytest or Playwright)

Call LLM with:

bug description

code context

existing tests (if any) in that area

Write the returned test code into the repo

Run tests and capture results

If no test can be generated, mark task as failed with a clear reason.

4.6 Test Runner

Main role: run tests and collect results.

Runs a fixed command, for example:

npm test, or

pytest, or

a command passed in config

Runs inside a Docker container or controlled environment

Captures:

exit code

stdout and stderr

test report paths if available

Returns a structured result object that the orchestrator can use.

4.7 Code Fix Agent

Main role: generate and apply a patch.

Input:

failing test output

bug description

relevant code snippets

repo file tree

Output:

one or more patches:

file path

line range or anchor

new code block

Steps:

Ask LLM for a patch in a strict format

Validate the patch:

does file exist

does it apply cleanly

Apply patch to the workspace

Run tests again

If tests pass, ready for PR. If not, stop after one or two attempts in MVP.

4.8 PR Creator

Main role: open the pull request once tests pass.

Behavior:

Create a branch name

Commit the changes

Push to remote

Open PR with:

title: simple and clear, for example Fix bug: <short summary>

body:

bug description

what code changed

which tests were added or updated

test results summary

Return PR URL to the API and store it with the task.

5. Data model (simple version)

You can start with a minimal schema:

Task

id

repo_url

bug_description

status (enum of the states above)

created_at

updated_at

workspace_path

branch_name

pr_url

logs (text or separate log table)

6. Constraints and defaults

Assume the repo is public or reachable from the worker

Assume a single test command per repo, stored in config

Limit:

maximum repo size (eg do not index node_modules)

maximum LLM context length, so use the index to narrow input

Hard stop after a small number of fix attempts per task

7. Success criteria for this MVP

A task is considered successful if:

The system cloned the repo

It generated a test that fails before the fix

It generated a patch that made the test pass

It opened a PR with both test and code changes

Your first goal is to get this working on one real repo end to end.
>>>>>>> 86c547f7711c6dd83180fdb4173ce339ed2c2aca
After that, you can generalize and improve each step.