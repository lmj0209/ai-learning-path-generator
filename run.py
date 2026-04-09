"""
This script handles the setup and execution of the web application.
"""
print("--- run.py started ---")
import os
from pathlib import Path
import shutil

from dotenv import load_dotenv

# On Render, environment variables are set via Dashboard – skip .env file logic
is_render = os.environ.get('RENDER')

if not is_render:
    # Load environment variables from .env file (local development only)
    env_path = Path('.env')
    env_example_path = Path('.env.example')

    # If .env doesn't exist, create it from example
    if not env_path.exists() and env_example_path.exists():
        shutil.copy(env_example_path, env_path)
        print("Created .env file from .env.example. Please update your API keys before proceeding.")

    # Load environment vars
    load_dotenv()
    print("--- dotenv loaded ---")
else:
    print("--- Running on Render, skipping .env file loading ---")

# Check if any API key is set
if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
    print("WARNING: Neither OPENAI_API_KEY nor DEEPSEEK_API_KEY found in environment variables.")
    if not is_render:
        # Only exit in local development; on Render, the app should still start
        print("Please set at least one API key before running the application.")
        exit(1)
    else:
        print("WARNING: Continuing without API key – some features will not work.")

# Create necessary directories
os.makedirs("vector_db", exist_ok=True)
os.makedirs("learning_paths", exist_ok=True)
print("--- API key checked and dirs created ---")

# Import and run Flask app
from web_app import create_app

app = create_app()
print("--- Flask app created via factory ---")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Disable debug mode to prevent auto-reloading issues
    debug = False

    print(f"Starting AI Learning Path Generator on port {port}")
    print("Visit http://localhost:5000 in your browser")

    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
