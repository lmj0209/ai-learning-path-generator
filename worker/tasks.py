"""
Celery tasks for learning path generation
Wraps existing logic from src/
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from celery_app import celery_app
import redis
from dotenv import load_dotenv

load_dotenv()

# Redis connection for status updates
REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL and REDIS_URL.startswith(('redis://', 'rediss://')):
    redis_client = redis.from_url(REDIS_URL, decode_responses=True, ssl_cert_reqs=None)
else:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True
    )


def update_task_status(task_id, status, progress, message):
    """Update task status in Redis"""
    task_key = f"task:{task_id}:meta"
    redis_client.hset(task_key, mapping={
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": datetime.utcnow().isoformat()
    })


@celery_app.task(bind=True, name='tasks.generate_learning_path_task')
def generate_learning_path_task(self, task_id, payload):
    """
    Generate a learning path using existing logic
    
    Args:
        task_id: Unique task identifier
        payload: Dict with topic, expertise_level, duration_weeks, time_commitment, etc.
    """
    try:
        # Update status: starting
        update_task_status(task_id, "processing", 5, "Initializing learning path generator...")
        
        # Import existing modules
        from src.learning_path import LearningPathGenerator
        
        # Extract parameters
        topic = payload.get('topic')
        expertise_level = payload.get('expertise_level', 'beginner')
        duration_weeks = int(payload.get('duration_weeks', 4))
        time_commitment = payload.get('time_commitment', 'moderate')
        goals = payload.get('goals', '')
        ai_provider = payload.get('ai_provider', 'openai')
        ai_model = payload.get('ai_model')
        
        # Update status: generating
        update_task_status(task_id, "processing", 10, "Analyzing your requirements...")
        
        # Initialize generator
        generator = LearningPathGenerator(
            ai_provider=ai_provider,
            ai_model=ai_model
        )
        
        # Update status: creating path
        update_task_status(task_id, "processing", 20, "Creating learning path structure...")
        
        # Generate the path
        learning_path = generator.generate(
            topic=topic,
            expertise_level=expertise_level,
            duration_weeks=duration_weeks,
            time_commitment=time_commitment,
            goals=goals
        )
        
        # Update status: fetching resources
        update_task_status(task_id, "processing", 60, "Searching for learning resources...")
        
        # The generate() method already handles resource fetching and validation
        # Progress updates happen within that method
        
        # Update status: finalizing
        update_task_status(task_id, "processing", 95, "Finalizing your learning path...")
        
        # Convert to dict for JSON serialization
        result = learning_path.dict() if hasattr(learning_path, 'dict') else learning_path
        
        # Store result in Redis
        result_key = f"task:{task_id}:result"
        redis_client.set(result_key, json.dumps(result))
        redis_client.expire(result_key, 86400)  # 24 hour TTL
        
        # Update status: complete
        task_key = f"task:{task_id}:meta"
        redis_client.hset(task_key, mapping={
            "status": "completed",
            "progress": 100,
            "message": "Learning path generated successfully!",
            "finished_at": datetime.utcnow().isoformat()
        })
        
        return {"task_id": task_id, "status": "completed"}
        
    except Exception as e:
        # Update status: failed
        error_message = str(e)
        task_key = f"task:{task_id}:meta"
        redis_client.hset(task_key, mapping={
            "status": "failed",
            "progress": 0,
            "message": "Task failed",
            "error_message": error_message,
            "finished_at": datetime.utcnow().isoformat()
        })
        
        # Re-raise for Celery to handle
        raise
