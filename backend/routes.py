"""
API Routes for task management
"""
import os
import uuid
import json
from flask import Blueprint, request, jsonify
from datetime import datetime
import redis

api_bp = Blueprint('api', __name__)

# Redis connection
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

@api_bp.route('/generate', methods=['POST'])
def generate_path():
    """
    Queue a learning path generation task
    Returns task_id immediately
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['topic', 'expertise_level', 'duration_weeks', 'time_commitment']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Store task metadata in Redis
        task_key = f"task:{task_id}:meta"
        redis_client.hset(task_key, mapping={
            "status": "queued",
            "progress": 0,
            "message": "Task queued, waiting to start...",
            "created_at": datetime.utcnow().isoformat(),
            "topic": data['topic'],
            "expertise_level": data['expertise_level']
        })
        redis_client.expire(task_key, 86400)  # 24 hour TTL
        
        # Store task payload
        payload_key = f"task:{task_id}:payload"
        redis_client.set(payload_key, json.dumps(data))
        redis_client.expire(payload_key, 86400)
        
        # Queue the task via Celery
        try:
            from worker.celery_app import celery_app
            celery_app.send_task(
                'worker.tasks.generate_learning_path_task',
                args=[task_id, data]
            )
        except Exception as e:
            print(f"Failed to queue task: {e}")
            # If Celery isn't available, just mark as queued
            # Worker will pick it up when it starts
            pass
        
        return jsonify({
            "task_id": task_id,
            "status": "queued",
            "message": "Learning path generation started"
        }), 202
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """
    Get the current status of a task
    """
    try:
        task_key = f"task:{task_id}:meta"
        task_data = redis_client.hgetall(task_key)
        
        if not task_data:
            return jsonify({"error": "Task not found"}), 404
        
        return jsonify({
            "task_id": task_id,
            "status": task_data.get('status', 'unknown'),
            "progress": int(task_data.get('progress', 0)),
            "message": task_data.get('message', ''),
            "created_at": task_data.get('created_at'),
            "finished_at": task_data.get('finished_at')
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/result/<task_id>', methods=['GET'])
def get_result(task_id):
    """
    Get the final result of a completed task
    """
    try:
        # Check task status first
        task_key = f"task:{task_id}:meta"
        task_data = redis_client.hgetall(task_key)
        
        if not task_data:
            return jsonify({"error": "Task not found"}), 404
        
        status = task_data.get('status')
        
        if status == 'processing' or status == 'queued':
            return jsonify({
                "error": "Task not yet complete",
                "status": status,
                "progress": int(task_data.get('progress', 0))
            }), 202
        
        if status == 'failed':
            return jsonify({
                "error": "Task failed",
                "message": task_data.get('error_message', 'Unknown error')
            }), 500
        
        # Get result
        result_key = f"task:{task_id}:result"
        result_data = redis_client.get(result_key)
        
        if not result_data:
            return jsonify({"error": "Result not found"}), 404
        
        return jsonify(json.loads(result_data)), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
