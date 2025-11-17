# ASA MVP Short Brief

## Goal of ASA MVP

The ASA MVP is an autonomous bug fixing system for a **single code repository**.

Given a Git repo URL and a human bug description, it should:

1. Clone and index the repo
2. Generate a failing test that reproduces the bug
3. Generate and apply a code fix in the same repo
4. Re-run the tests
5. Open a pull request with the new test(s) and code fix

If it cannot do this, it should fail clearly, with a clean task status and logs that explain where it got stuck.

No feature design, no multi-repo changes, no infra as code, no architecture planning.

## Inputs and outputs

### Inputs

For each bug-fix task, the system receives:

* `repo_url`: Git URL for a **single** repo
* `bug_description`: Free-text description of the bug from the user

You can optionally support:

* `test_command` (string, optional): If not provided, use a default from config (for example `pytest` or `npm test`).

Inputs arrive through:

* A REST endpoint: `POST /api/v1/task/submit` (FastAPI)
* A simple web form in React that lets a user paste the repo URL and bug description and see task status later.

### Outputs

For each task, the system should produce:

* **Primary output:**

  * A Git branch with:

    * One or more new or updated tests that show the bug
    * Code changes that make the tests pass
  * A Pull Request link on the target Git host (GitHub, etc.)

* **Status and logs (via API / UI):**

  * Current state (for example: `CLONING_REPO`, `INDEXING_CODE`, `GENERATING_TEST`, `RUNNING_TESTS`, `GENERATING_FIX`, `OPENING_PR`, `COMPLETED`, `FAILED`)
  * High-level log messages per step
  * If failed: a clear reason (for example “could not run tests”, “could not generate failing test”, “fix did not make tests pass”)

This is enough for a developer to review the PR and either merge or close it.

## Main components (high level)

This MVP only needs a **thin** set of services that together can run a single bug-fix loop end-to-end. You can think of them as: API, orchestrator, repo manager, indexer, test agent, fix agent, and PR creator.

### 1. API + simple UI

**Backend (FastAPI)**

* `POST /api/v1/task/submit`

  * Input: `repo_url`, `bug_description`, optional `test_command`
  * Output: `task_id`, initial status
* `GET /api/v1/task/{task_id}`

  * Returns current status, short logs, and PR URL if ready

**Frontend (React, optional but nice)**

* A simple page with:

  * Form to submit a task
  * A task status view that polls the backend and shows the state, logs, and PR link

### 2. Task orchestrator (state machine)

A small orchestrator service runs the steps for a task in order. You can implement this as plain Python code, or with a simple state machine library.

Typical states:

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

Responsibilities:

* Move the task from one state to the next
* Call the right service (repo manager, indexer, test agent, fix agent, PR creator)
* Write short logs for each step
* Stop early on errors and mark the task as `FAILED` with a clear reason

### 3. Repo manager (Git operations)

A small Python service that does all the Git work for a **single** repo.

Responsibilities:

* Clone the repo to a local workspace: `workspaces/{task_id}`
* Checkout the base branch (for example `main`)
* Create a fix branch (for example `asa/fix/{task_id}`)
* Apply patches created by the fix agent
* Commit and push the branch
* Open a PR via the Git provider API or CLI and return the PR URL

### 4. Code indexer (minimal Codebase Guardian)

This is the **Structured Context Model (SCM)** in a very simple form: AST + embeddings.

Responsibilities:

* Walk the repo (ignore large folders like `node_modules`, `dist`, `build`)
* For supported languages (start with one, like Python or TypeScript):

  * Parse files into an AST (for example with tree-sitter)
  * Extract top-level symbols (functions, classes)
  * Chunk code into small pieces
  * Build embeddings for each chunk and store in a local vector store (for example ChromaDB)
* Provide a function:

  ```python
  search_relevant_code(bug_description) -> list[CodeSnippet]
  ```

  where each `CodeSnippet` has:

  * file path
  * line range
  * snippet text

This index does not need to be perfect, it just has to narrow the context so the LLM sees only the most relevant code when generating tests and fixes.

### 5. Test generator and runner (CIT agent + sandbox)

This is the **Behavioral Verification Pipeline (BVP)**, but kept small.

**Test generator**

* Input:

  * `bug_description`
  * Relevant code snippets from the indexer
  * Any nearby existing tests
* Output:

  * One or more test files in the repo, for example:

    * `tests/test_bug_{task_id}.py` or
    * `tests/asa/test_bug_{task_id}.ts`

Steps:

1. Call the LLM with a strict prompt to produce a single failing test.
2. Save the test file into the repo.
3. Ask the test runner to run the tests and confirm that this new test fails in the expected way.

If you cannot create a failing test, mark the task as `FAILED` and log that clearly.

**Test runner**

* Runs a fixed command (for example `pytest` or `npm test`) in a controlled environment, ideally a Docker sandbox.
* Returns:

  * Exit code
  * stdout / stderr
  * Structured test result summary (which test failed, error message, etc.)

### 6. Code fix agent

This is the LLM-driven agent that creates the patch.

Inputs:

* Bug description
* Failing test output
* Relevant code snippets and file paths
* Maybe a small view of the repo tree near those files

Outputs:

* One or more patches described as:

  * `file_path`
  * `start_line` / `end_line` or a clear anchor
  * `new_code_block`

Steps:

1. Ask the LLM for a patch in a strict JSON format.
2. Validate that the target file exists and the patch can be applied.
3. Apply the patch in the workspace.
4. Trigger the test runner again.

If tests pass, the orchestrator moves on to PR creation.
If tests still fail, the MVP can stop after one attempt (or at most two) and mark the task as `FAILED`.

### 7. PR creator and simple data model

**PR creator**

* Commit changes (tests + code) on the fix branch
* Push the branch
* Open a PR with:

  * Title, for example: `Fix bug: <short summary>`
  * Body with:

    * Original bug description
    * What changed
    * Which tests were added or updated
    * Short test result summary

**Minimal data model**

You can start with a single `Task` table or document:

* `id`
* `repo_url`
* `bug_description`
* `status` (state enum)
* `created_at`, `updated_at`
* `workspace_path`
* `branch_name`
* `pr_url` (nullable)
* `logs` (text or pointer to a log file)

## What is clearly out of scope for now

For this ASA MVP, you will **not** build:

* Any work across more than one repo at a time
* Any feature planning or big architecture planner
* Any infrastructure-as-code or cloud deployment changes
* Any integration with ticket systems (JIRA, Linear, etc.)
* Any knowledge graph or complex codebase graph beyond simple AST + vector index
* Any long-running scheduler or cron, beyond what is needed to finish one task
* Any deep production hardening like:

  * SBOM and supply-chain tooling
  * Rate limiting per user
  * License allowlists and redaction policies
  * Detailed OpenTelemetry tracing and strict token budgets

Those items live in the larger “Ultimate Master Blueprint” and can be added later, once you have a simple, reliable loop that can take **one bug in one repo**, produce a failing test, generate a fix, make the tests pass, and open a PR.
