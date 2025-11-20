# ASA Sandbox - Hardened Container Environment

Secure, isolated Docker container for running bug fixes and tests.

## Security Features

### 1. Resource Limits
- **Max Processes**: 100 (prevents fork bombs)
- **File Descriptors**: 1024
- **CPU Time**: 600s per process
- **File Size**: 100MB max
- **Virtual Memory**: 2GB max

### 2. Network Restrictions
- Network disabled by default (`--network none`)
- Outbound connections blocked
- Only allowed: package registries (via proxy if needed)

### 3. File System
- Read-only root filesystem
- Writable only in `/workspace`
- Temporary files in `/workspace/.tmp`
- No access to host filesystem

### 4. User Permissions
- Runs as non-root user (`sandbox`, UID 1000)
- No sudo/root access
- Limited capabilities

### 5. Environment Sanitization
- Sensitive env vars stripped
- No secrets passed to container
- Isolated environment

## Building the Image

```bash
cd sandbox
docker build -t asa-sandbox:latest .
```

## Running the Sandbox

### Basic Usage

```bash
# Run with network disabled (recommended)
docker run --rm -it \
  --network none \
  --read-only \
  --tmpfs /workspace:rw,noexec,nosuid,size=1G \
  asa-sandbox:latest
```

### Running Tests

```bash
# Mount code and run tests
docker run --rm \
  --network none \
  --read-only \
  -v $(pwd)/repo:/workspace:ro \
  --tmpfs /workspace/.tmp:rw,noexec,nosuid,size=100M \
  -e TIMEOUT=300 \
  asa-sandbox:latest \
  pytest /workspace/tests
```

### With Limited Network (for package installation)

```bash
# Allow network for package installation only
docker run --rm \
  -v $(pwd)/repo:/workspace:rw \
  asa-sandbox:latest \
  pip install -r requirements.txt

# Then run tests with network disabled
docker run --rm \
  --network none \
  -v $(pwd)/repo:/workspace:ro \
  --tmpfs /workspace/.tmp:rw \
  asa-sandbox:latest \
  pytest /workspace/tests
```

## Security Best Practices

### 1. Never Pass Secrets

```bash
# ❌ BAD - Don't do this
docker run -e GITHUB_TOKEN=$GITHUB_TOKEN asa-sandbox

# ✅ GOOD - Use volume mounts for code only
docker run -v $(pwd)/code:/workspace:ro asa-sandbox
```

### 2. Always Use --network none

```bash
# ❌ BAD - Default network allows outbound connections
docker run asa-sandbox

# ✅ GOOD - Disable network
docker run --network none asa-sandbox
```

### 3. Use Read-Only Filesystem

```bash
# ✅ GOOD - Read-only root, writable tmpfs
docker run \
  --read-only \
  --tmpfs /workspace/.tmp:rw,noexec,nosuid \
  asa-sandbox
```

### 4. Set Resource Limits

```bash
# ✅ GOOD - Limit CPU and memory
docker run \
  --cpus=2.0 \
  --memory=2g \
  --memory-swap=2g \
  --pids-limit=100 \
  asa-sandbox
```

## Integration with ASA Backend

The sandbox is used by `backend/app/services/sandbox_service.py`:

```python
from app.services.sandbox_service import SandboxService

sandbox = SandboxService()

# Run tests in isolated environment
result = sandbox.run_tests(
    repo_path="/path/to/repo",
    test_command="pytest tests/",
    timeout=300,
    network_enabled=False
)
```

## Monitoring

View sandbox logs:

```bash
# View container logs
docker logs <container_id>

# Monitor resource usage
docker stats <container_id>
```

## Cleanup

```bash
# Remove stopped containers
docker container prune

# Remove sandbox image
docker rmi asa-sandbox:latest
```

## Troubleshooting

### "Permission denied" errors

Ensure files are readable:
```bash
chmod -R a+r repo/
```

### Network errors during pip install

Use two-stage approach:
1. Install deps with network
2. Run tests with network disabled

### Resource limit exceeded

Adjust ulimits in `entrypoint.sh` or Docker run command.

## Advanced Configuration

### Custom Entrypoint

```bash
docker run \
  --entrypoint /bin/bash \
  asa-sandbox:latest \
  -c "echo 'Custom command'"
```

### Adding Languages

Edit `Dockerfile` to add support for other languages:

```dockerfile
# Add Ruby
RUN apt-get install -y ruby-full
RUN gem install bundler rspec

# Add Go
RUN wget https://go.dev/dl/go1.21.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf go1.21.linux-amd64.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"
```

## Security Audit

Regular security checks:

```bash
# Scan image for vulnerabilities
docker scan asa-sandbox:latest

# Check for secrets in image
docker history asa-sandbox:latest

# Verify user is non-root
docker run asa-sandbox:latest whoami  # Should output: sandbox
```
