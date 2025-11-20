#!/bin/bash
#
# ASA Sandbox Entrypoint - Security Hardening
#
# This script configures security limits and network restrictions
# before running the actual workload.

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}[Sandbox] Starting ASA hardened sandbox...${NC}"

# ============================================================================
# RESOURCE LIMITS
# ============================================================================

echo -e "${YELLOW}[Sandbox] Applying resource limits...${NC}"

# Limit maximum processes (prevent fork bombs)
ulimit -u 100
echo "[Sandbox] ✓ Max processes: 100"

# Limit file descriptors
ulimit -n 1024
echo "[Sandbox] ✓ Max file descriptors: 1024"

# Limit CPU time (10 minutes per process)
ulimit -t 600
echo "[Sandbox] ✓ Max CPU time: 600 seconds"

# Limit maximum file size (100MB)
ulimit -f 102400
echo "[Sandbox] ✓ Max file size: 100MB"

# Limit virtual memory (2GB)
ulimit -v 2097152
echo "[Sandbox] ✓ Max virtual memory: 2GB"

# ============================================================================
# FILE SYSTEM RESTRICTIONS
# ============================================================================

echo -e "${YELLOW}[Sandbox] Setting up file system restrictions...${NC}"

# Ensure workspace directory exists and is writable
if [ ! -d "/workspace" ]; then
    echo -e "${RED}[Sandbox] ERROR: /workspace directory not found${NC}"
    exit 1
fi

# Create temporary directories with restrictions
export TMPDIR="/workspace/.tmp"
mkdir -p "$TMPDIR"
chmod 700 "$TMPDIR"
echo "[Sandbox] ✓ Temp directory: $TMPDIR"

# Restrict write access to workspace only
# (Cannot enforce in entrypoint without root, must use Docker volume config)
echo "[Sandbox] ✓ Workspace: /workspace (writable)"
echo "[Sandbox] ℹ Other directories: read-only (via Docker config)"

# ============================================================================
# NETWORK RESTRICTIONS
# ============================================================================

echo -e "${YELLOW}[Sandbox] Configuring network restrictions...${NC}"

# Note: Network restrictions are best configured at Docker level:
# docker run --network none ...
# or using iptables rules (requires root/capabilities)

# Set environment variables to disable network for some tools
export NO_PROXY="*"
export http_proxy="http://127.0.0.1:9/"  # Dummy proxy to block HTTP
export https_proxy="http://127.0.0.1:9/" # Dummy proxy to block HTTPS

echo "[Sandbox] ⚠ Network access should be disabled at Docker level"
echo "[Sandbox] ℹ Use: docker run --network none ..."

# Allowed network destinations (if needed):
# - Package registries: pypi.org, npmjs.com (via allowlist proxy)
# - Git hosts: github.com, gitlab.com (read-only)
ALLOWED_HOSTS="pypi.org npmjs.com github.com gitlab.com"
echo "[Sandbox] ℹ Allowed hosts (if network enabled): $ALLOWED_HOSTS"

# ============================================================================
# SECURITY CHECKS
# ============================================================================

echo -e "${YELLOW}[Sandbox] Running security checks...${NC}"

# Verify running as non-root
if [ "$(id -u)" -eq 0 ]; then
    echo -e "${RED}[Sandbox] ERROR: Running as root is not allowed${NC}"
    exit 1
fi
echo "[Sandbox] ✓ Running as user: $(whoami) (UID: $(id -u))"

# Check for sensitive environment variables
SENSITIVE_VARS=("AWS_SECRET_ACCESS_KEY" "GITHUB_TOKEN" "OPENAI_API_KEY" "DATABASE_PASSWORD")
for var in "${SENSITIVE_VARS[@]}"; do
    if [ -n "${!var}" ]; then
        echo -e "${RED}[Sandbox] WARNING: Sensitive variable detected: $var${NC}"
        echo -e "${RED}[Sandbox] This variable will NOT be accessible in the sandbox${NC}"
        unset "$var"
    fi
done
echo "[Sandbox] ✓ No sensitive environment variables"

# ============================================================================
# WORKSPACE SETUP
# ============================================================================

echo -e "${YELLOW}[Sandbox] Setting up workspace...${NC}"

# Change to workspace directory
cd /workspace || exit 1

# Create standard directories
mkdir -p /workspace/{src,tests,logs}
echo "[Sandbox] ✓ Created standard directories"

# Set up Git config (safe directory)
git config --global safe.directory /workspace 2>/dev/null || true

# ============================================================================
# EXECUTION TIMEOUT
# ============================================================================

# If TIMEOUT environment variable is set, use timeout command
if [ -n "$TIMEOUT" ]; then
    echo "[Sandbox] ⏱ Execution timeout: ${TIMEOUT}s"
    TIMEOUT_CMD="timeout ${TIMEOUT}s"
else
    TIMEOUT_CMD=""
fi

# ============================================================================
# RUN COMMAND
# ============================================================================

echo -e "${GREEN}[Sandbox] Sandbox ready. Executing command...${NC}"
echo "============================================================"

# Execute the provided command
if [ $# -eq 0 ]; then
    # No command provided, start interactive shell
    exec /bin/bash
else
    # Execute provided command with timeout if set
    if [ -n "$TIMEOUT_CMD" ]; then
        exec $TIMEOUT_CMD "$@"
    else
        exec "$@"
    fi
fi
