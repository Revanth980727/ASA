"""
Services package for ASA MVP.

This package contains the core services for the autonomous bug fixing system:
- orchestrator: TaskOrchestrator that manages the bug-fixing workflow state machine
- repo_manager: RepoManager for Git operations (clone, branch, commit, PR)
- code_index: CodeIndex for AST parsing and vector embeddings
- test_runner: TestRunner for executing tests in a sandbox
- fix_agent: FixAgent for LLM-driven code fix generation
"""
