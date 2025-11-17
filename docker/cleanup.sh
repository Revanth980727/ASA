#!/bin/bash
# Cleanup script for ASA sandbox containers
#
# Usage:
#   ./docker/cleanup.sh           # Remove stopped containers
#   ./docker/cleanup.sh --all     # Remove all ASA containers
#   ./docker/cleanup.sh --force   # Force remove running containers

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}ASA Container Cleanup${NC}"
echo "====================="
echo ""

# Parse arguments
FORCE=false
ALL=false

for arg in "$@"; do
    case $arg in
        --force)
            FORCE=true
            ;;
        --all)
            ALL=true
            ;;
    esac
done

# Find ASA containers
echo "Finding ASA sandbox containers..."

if [ "$FORCE" = true ]; then
    # Force remove all running and stopped containers
    echo -e "${YELLOW}Force removing all ASA containers...${NC}"
    docker ps -a --filter "label=com.asa.type=sandbox" --format "{{.ID}}" | xargs -r docker rm -f
elif [ "$ALL" = true ]; then
    # Remove all stopped containers
    echo -e "${YELLOW}Removing all stopped ASA containers...${NC}"
    docker ps -a --filter "label=com.asa.type=sandbox" --filter "status=exited" --format "{{.ID}}" | xargs -r docker rm
else
    # Remove only auto-cleanup containers
    echo "Removing containers marked for auto-cleanup..."
    docker ps -a --filter "label=com.asa.auto_cleanup=true" --filter "status=exited" --format "{{.ID}}" | xargs -r docker rm
fi

# Count remaining containers
REMAINING=$(docker ps -a --filter "label=com.asa.type=sandbox" --format "{{.ID}}" | wc -l)

echo ""
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo "Remaining ASA containers: $REMAINING"

if [ $REMAINING -gt 0 ]; then
    echo ""
    echo "Active containers:"
    docker ps --filter "label=com.asa.type=sandbox" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.CreatedAt}}"
fi

# Cleanup dangling volumes
echo ""
echo "Cleaning up dangling volumes..."
docker volume prune -f

echo ""
echo -e "${GREEN}Done!${NC}"
