"""
Redis-based worker for processing map generation jobs.
Replaces AWS SQS polling with local Redis queue.
"""

import os
import json
import signal
import sys
import traceback
from datetime import datetime

import redis

from process_request import process_map_request


# Configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
QUEUE_NAME = "map_jobs"
WORK_DIR = os.environ.get("WORK_DIR", "/data/maps")

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    global shutdown_requested
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    shutdown_requested = True


def update_job_status(r: redis.Redis, job_id: str, status: str, data: dict = None):
    """Update job status in Redis."""
    result = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if data:
        result.update(data)
    r.set(f"result:{job_id}", json.dumps(result))


def main():
    global shutdown_requested

    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    # Test connection
    try:
        r.ping()
        print("Connected to Redis")
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    print(f"Worker started. Polling queue '{QUEUE_NAME}'...")
    print(f"Work directory: {WORK_DIR}")

    while not shutdown_requested:
        try:
            # Block until a job is available (timeout after 5 seconds to check shutdown flag)
            result = r.brpop(QUEUE_NAME, timeout=5)

            if result is None:
                # Timeout, check shutdown flag and continue
                continue

            queue_name, job_data = result
            print(f"\n{'='*50}")
            print(f"Received job at {datetime.now().isoformat()}")

            try:
                job = json.loads(job_data)
                job_id = job.get("id", "unknown")
                print(f"Job ID: {job_id}")

                # Update status to processing
                update_job_status(r, job_id, "processing")

                # Process the job
                result = process_map_request(job, WORK_DIR)

                # Update status to completed
                update_job_status(r, job_id, "completed", result)
                print(f"Job {job_id} completed successfully")

            except json.JSONDecodeError as e:
                print(f"Invalid JSON in job data: {e}")
                continue

            except Exception as e:
                print(f"Job processing failed: {e}")
                traceback.print_exc()

                if "job_id" in dir():
                    update_job_status(r, job_id, "failed", {
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    })

        except redis.ConnectionError as e:
            print(f"Redis connection lost: {e}")
            print("Attempting to reconnect in 5 seconds...")
            import time
            time.sleep(5)
            try:
                r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
                r.ping()
                print("Reconnected to Redis")
            except:
                pass

    print("Worker shutdown complete")


if __name__ == "__main__":
    main()
