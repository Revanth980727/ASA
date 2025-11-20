"""
Background task queue with RQ and backpressure controls.

This module provides a production-grade task queue using Redis Queue (RQ) with:
- Hard limits on queue size and concurrent workers
- Per-user concurrent task limits
- Task cancellation support
- Job status tracking
"""

import redis
from rq import Queue, Worker
from rq.job import Job, JobStatus
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueueConfig:
    """Configuration for queue limits and backpressure."""

    # Redis connection
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0

    # Queue limits
    MAX_QUEUE_SIZE = 100  # Maximum tasks in queue
    MAX_CONCURRENT_JOBS = 5  # Maximum concurrent workers
    MAX_PER_USER_CONCURRENT = 2  # Maximum concurrent tasks per user

    # Job timeouts
    JOB_TIMEOUT = 3600  # 1 hour per task
    RESULT_TTL = 86400  # Keep results for 24 hours
    FAILURE_TTL = 604800  # Keep failures for 7 days

    # Queue names
    DEFAULT_QUEUE = "asa_tasks"
    HIGH_PRIORITY_QUEUE = "asa_tasks_high"


class TaskQueue:
    """Wrapper around RQ for managing ASA task queue."""

    def __init__(self, config: QueueConfig = None):
        """Initialize task queue with Redis connection."""
        self.config = config or QueueConfig()

        # Connect to Redis
        # Note: decode_responses=False is required for RQ (uses pickle serialization)
        self.redis_conn = redis.Redis(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            db=self.config.REDIS_DB,
            decode_responses=False  # RQ requires binary mode for pickle
        )

        # Create queues
        self.default_queue = Queue(
            self.config.DEFAULT_QUEUE,
            connection=self.redis_conn
        )
        self.high_priority_queue = Queue(
            self.config.HIGH_PRIORITY_QUEUE,
            connection=self.redis_conn
        )

    def get_queue_size(self, queue_name: str = None) -> int:
        """Get current size of the queue."""
        queue = self._get_queue(queue_name)
        return len(queue)

    def get_active_jobs_count(self) -> int:
        """Get count of currently running jobs across all workers."""
        workers = Worker.all(connection=self.redis_conn)
        active_count = 0
        for worker in workers:
            if worker.get_current_job():
                active_count += 1
        return active_count

    def get_user_active_jobs(self, user_id: str) -> List[Job]:
        """Get all active jobs for a specific user."""
        workers = Worker.all(connection=self.redis_conn)
        user_jobs = []

        for worker in workers:
            current_job = worker.get_current_job()
            if current_job and current_job.meta.get("user_id") == user_id:
                user_jobs.append(current_job)

        # Also check queued jobs
        for job in self.default_queue.jobs:
            if job.meta.get("user_id") == user_id and job.get_status() == JobStatus.QUEUED:
                user_jobs.append(job)

        return user_jobs

    def can_enqueue(self, user_id: Optional[str] = None) -> tuple[bool, str]:
        """
        Check if a new task can be enqueued based on backpressure limits.

        Returns:
            (can_enqueue: bool, reason: str)
        """
        # Check global queue size limit
        queue_size = self.get_queue_size()
        if queue_size >= self.config.MAX_QUEUE_SIZE:
            return False, f"Queue is full ({queue_size}/{self.config.MAX_QUEUE_SIZE})"

        # Check concurrent jobs limit
        active_jobs = self.get_active_jobs_count()
        if active_jobs >= self.config.MAX_CONCURRENT_JOBS:
            return False, f"Maximum concurrent jobs reached ({active_jobs}/{self.config.MAX_CONCURRENT_JOBS})"

        # Check per-user concurrent limit
        if user_id:
            user_active = len(self.get_user_active_jobs(user_id))
            if user_active >= self.config.MAX_PER_USER_CONCURRENT:
                return False, f"User has too many active tasks ({user_active}/{self.config.MAX_PER_USER_CONCURRENT})"

        return True, "OK"

    def enqueue_task(
        self,
        func,
        task_id: str,
        user_id: Optional[str] = None,
        high_priority: bool = False,
        **kwargs
    ) -> Optional[Job]:
        """
        Enqueue a task with backpressure checks.

        Args:
            func: The function to execute
            task_id: Task ID for tracking
            user_id: User ID for per-user limits
            high_priority: Use high priority queue
            **kwargs: Arguments to pass to the function

        Returns:
            Job object if enqueued, None if rejected
        """
        # Check if we can enqueue
        can_enqueue, reason = self.can_enqueue(user_id)
        if not can_enqueue:
            logger.warning(f"Cannot enqueue task {task_id}: {reason}")
            return None

        # Select queue
        queue = self.high_priority_queue if high_priority else self.default_queue

        # Enqueue with metadata
        # Note: job_timeout=None disables timeout (required for Windows compatibility)
        job = queue.enqueue(
            func,
            task_id,
            job_timeout=None,  # None means no timeout (Windows compatible)
            result_ttl=self.config.RESULT_TTL,
            failure_ttl=self.config.FAILURE_TTL,
            meta={
                "task_id": task_id,
                "user_id": user_id,
                "enqueued_at": datetime.utcnow().isoformat()
            },
            **kwargs
        )

        logger.info(f"Enqueued task {task_id} as job {job.id}")
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        try:
            return Job.fetch(job_id, connection=self.redis_conn)
        except Exception as e:
            logger.error(f"Error fetching job {job_id}: {e}")
            return None

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a job."""
        job = self.get_job(job_id)
        if not job:
            return None

        return {
            "job_id": job.id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "result": job.result,
            "exc_info": job.exc_info,
            "meta": job.meta
        }

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a queued or running job.

        Note: For running jobs, this sends a stop signal. The worker
        must check for cancellation and stop gracefully.
        """
        job = self.get_job(job_id)
        if not job:
            logger.warning(f"Cannot cancel job {job_id}: not found")
            return False

        try:
            status = job.get_status()

            if status == JobStatus.QUEUED:
                # Remove from queue
                job.cancel()
                logger.info(f"Cancelled queued job {job_id}")
                return True

            elif status in (JobStatus.STARTED, JobStatus.DEFERRED):
                # Send stop signal for running jobs
                job.cancel()
                # Mark in metadata for worker to check
                job.meta["cancelled"] = True
                job.meta["cancelled_at"] = datetime.utcnow().isoformat()
                job.save_meta()
                logger.info(f"Sent cancellation signal to running job {job_id}")
                return True

            else:
                logger.warning(f"Cannot cancel job {job_id}: status is {status}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    def is_job_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled (for worker to check periodically)."""
        job = self.get_job(job_id)
        if not job:
            return False
        return job.meta.get("cancelled", False)

    def cleanup_old_jobs(self, days: int = 7):
        """Clean up jobs older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get all jobs from all queues
        for queue in [self.default_queue, self.high_priority_queue]:
            for job in queue.jobs:
                if job.ended_at and job.ended_at < cutoff:
                    job.delete()
                    logger.info(f"Cleaned up old job {job.id}")

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        workers = Worker.all(connection=self.redis_conn)

        return {
            "queue_size": self.get_queue_size(),
            "high_priority_queue_size": len(self.high_priority_queue),
            "active_jobs": self.get_active_jobs_count(),
            "total_workers": len(workers),
            "limits": {
                "max_queue_size": self.config.MAX_QUEUE_SIZE,
                "max_concurrent_jobs": self.config.MAX_CONCURRENT_JOBS,
                "max_per_user_concurrent": self.config.MAX_PER_USER_CONCURRENT
            }
        }

    def _get_queue(self, queue_name: Optional[str] = None) -> Queue:
        """Get queue by name."""
        if queue_name == self.config.HIGH_PRIORITY_QUEUE:
            return self.high_priority_queue
        return self.default_queue


# Global queue instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get or create the global task queue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
