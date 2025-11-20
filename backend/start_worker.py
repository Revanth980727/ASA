"""
Windows-compatible RQ worker script.

On Windows, we need to use SimpleWorker instead of the default Worker
because Windows doesn't support os.fork() or signal.SIGALRM.
"""

import sys
import signal
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Patch signal module for Windows compatibility BEFORE importing RQ
if not hasattr(signal, 'SIGALRM'):
    # Create a dummy SIGALRM that won't actually be used
    signal.SIGALRM = signal.SIGTERM  # Use SIGTERM as a stand-in

    # Patch the signal function to ignore SIGALRM
    _original_signal = signal.signal
    def _patched_signal(sig, handler):
        if sig == signal.SIGALRM:
            # Ignore SIGALRM on Windows
            return lambda *args: None
        return _original_signal(sig, handler)
    signal.signal = _patched_signal

    # Patch signal.alarm() which doesn't exist on Windows
    def _dummy_alarm(seconds):
        # Do nothing on Windows
        return 0
    signal.alarm = _dummy_alarm

from redis import Redis
from rq import Queue
from rq.worker import SimpleWorker

# Connect to Redis
# Note: decode_responses=False is required for RQ (uses pickle serialization)
redis_conn = Redis(host='localhost', port=6379, db=0, decode_responses=False)

# Create queue
queue = Queue('asa_tasks', connection=redis_conn)

# Create SimpleWorker (works on Windows, timeouts are disabled by default)
worker = SimpleWorker(
    [queue],
    connection=redis_conn
)

print(f"Starting worker for queue: asa_tasks")
print(f"Worker class: SimpleWorker (Windows compatible)")
print(f"Press Ctrl+C to stop")
print("")

# Start the worker
try:
    worker.work(with_scheduler=False, burst=False)
except KeyboardInterrupt:
    print("\nWorker stopped by user")
    sys.exit(0)
