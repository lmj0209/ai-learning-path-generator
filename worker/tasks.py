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

# This file now contains a simple function for the RQ worker.

def generate_learning_path_for_worker(payload):
    """
    Worker function to generate a learning path. 
    This is the function that the RQ worker will execute.
    
    Args:
        payload (dict): A dictionary containing the necessary parameters like 
                        'topic', 'expertise_level', etc.
    """
    print(f"Worker received job with payload: {payload}")
    
    # Import necessary modules inside the function
    # This is a best practice for RQ tasks
    from src.learning_path import LearningPathGenerator

    # Extract parameters from the payload
    topic = payload.get('topic')
    expertise_level = payload.get('expertise_level', 'beginner')
    duration_weeks = int(payload.get('duration_weeks', 4))
    time_commitment = payload.get('time_commitment', 'moderate')
    goals = payload.get('goals', '')
    ai_provider = payload.get('ai_provider', 'openai')
    ai_model = payload.get('ai_model')

    # Initialize the generator
    generator = LearningPathGenerator(
        ai_provider=ai_provider,
        ai_model=ai_model
    )

    # Generate the learning path
    # The result of this function will be stored in Redis by RQ
    learning_path = generator.generate(
        topic=topic,
        expertise_level=expertise_level,
        duration_weeks=duration_weeks,
        time_commitment=time_commitment,
        goals=goals
    )

    # The learning_path object (likely a Pydantic model) will be pickled by RQ 
    # and stored in Redis. The API can then fetch this result.
    print(f"Successfully generated learning path for topic: {topic}")
    return learning_path.dict() if hasattr(learning_path, 'dict') else learning_path
