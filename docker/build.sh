#!/bin/bash
# Build script for ASA sandbox Docker image
#
# Usage:
#   ./docker/build.sh
#   ./docker/build.sh --no-cache

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="asa-sandbox"
IMAGE_TAG="latest"
DOCKERFILE="docker/Dockerfile.sandbox"

echo -e "${GREEN}Building ASA Sandbox Docker Image${NC}"
echo "======================================"
echo "Image: $IMAGE_NAME:$IMAGE_TAG"
echo "Dockerfile: $DOCKERFILE"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Parse arguments
BUILD_ARGS=""
if [[ "$1" == "--no-cache" ]]; then
    BUILD_ARGS="--no-cache"
    echo -e "${YELLOW}Building with --no-cache${NC}"
fi

# Build image
echo -e "${GREEN}Building image...${NC}"
docker build \
    $BUILD_ARGS \
    -f "$DOCKERFILE" \
    -t "$IMAGE_NAME:$IMAGE_TAG" \
    .

# Check if build was successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Build successful!${NC}"
    echo ""
    echo "Image details:"
    docker images "$IMAGE_NAME:$IMAGE_TAG"
    echo ""
    echo "To run a test container:"
    echo "  docker run --rm -it $IMAGE_NAME:$IMAGE_TAG /bin/bash"
    echo ""
    echo "To test with workspace:"
    echo "  docker run --rm -v \$(pwd)/workspace:/workspace $IMAGE_NAME:$IMAGE_TAG python3 --version"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
