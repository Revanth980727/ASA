"""
RQ Worker entry point for ASA background task processing.

This script starts an RQ worker that processes tasks from the Redis queue.
Workers pull tasks from the queue and execute the autonomous bug-fixing loop.

Usage:
    python worker.py                    # Start worker on default queue
    python worker.py --queue high       # Start worker on high-priority queue
    python worker.py --burst            # Run in burst mode (exit when done)

Environment Variables:
    REDIS_HOST: Redis server host (default: localhost)
    REDIS_PORT: Redis server port (default: 6379)
    REDIS_DB: Redis database number (default: 0)
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import redis
from rq import Worker, Queue, Connection
from rq.logutils import setup_loggers

from app.services.queue import QueueConfig
from app.services.worker_tasks import run_task_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("worker.log")
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Start the RQ worker."""
    import argparse

    parser = argparse.ArgumentParser(description="ASA RQ Worker")
    parser.add_argument(
        "--queue",
        choices=["default", "high"],
        default="default",
        help="Queue to process (default or high priority)"
    )
    parser.add_argument(
        "--burst",
        action="store_true",
        help="Run in burst mode (exit when queue is empty)"
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Worker name (default: auto-generated)"
    )

    args = parser.parse_args()

    # Get Redis configuration from environment or use defaults
    redis_host = os.getenv("REDIS_HOST", QueueConfig.REDIS_HOST)
    redis_port = int(os.getenv("REDIS_PORT", QueueConfig.REDIS_PORT))
    redis_db = int(os.getenv("REDIS_DB", QueueConfig.REDIS_DB))

    # Connect to Redis
    redis_conn = redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        decode_responses=True
    )

    # Test connection
    try:
        redis_conn.ping()
        logger.info(f"Connected to Redis at {redis_host}:{redis_port}/{redis_db}")
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.error("Make sure Redis is running: redis-server")
        sys.exit(1)

    # Select queue
    queue_name = QueueConfig.HIGH_PRIORITY_QUEUE if args.queue == "high" else QueueConfig.DEFAULT_QUEUE
    logger.info(f"Listening on queue: {queue_name}")

    # Setup RQ logging
    setup_loggers(logging.INFO)

    # Create and start worker
    with Connection(redis_conn):
        worker = Worker(
            [queue_name],
            connection=redis_conn,
            name=args.name
        )

        logger.info(f"Starting worker: {worker.name}")
        logger.info(f"Burst mode: {args.burst}")

        try:
            worker.work(burst=args.burst, with_scheduler=True)
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    main()
