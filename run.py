"""
This script handles the setup and execution of the web application.
"""
print("--- run.py started ---")
import os
import sys
from pathlib import Path
import shutil

# Fix: PEP 649 (Python 3.14+) breaks pydantic v1 in multiple ways.
# This patch must run BEFORE any pydantic/langchain/langsmith import.
if sys.version_info >= (3, 14):
    try:
        from pydantic.main import ModelMetaclass as _MC
        import builtins as _builtins

        _builtin_types = {
            name: obj for name, obj in vars(_builtins).items()
            if isinstance(obj, type)
        }

        # Fix 1: Ensure __annotations__ is populated from __annotate_func__
        _orig_mc_new = _MC.__new__

        def _patched_mc_new(mcs, name, bases, namespace, **kwargs):
            if '__annotations__' not in namespace and '__annotate_func__' in namespace:
                try:
                    namespace['__annotations__'] = namespace['__annotate_func__'](1)
                except Exception:
                    pass
            return _orig_mc_new(mcs, name, bases, namespace, **kwargs)

        _MC.__new__ = staticmethod(_patched_mc_new)

        # Fix 2: PEP 649 resolves builtin type names (dict, list, etc.) to
        # class methods (e.g. BaseModel.dict) instead of the actual builtins.
        # This happens inside generic aliases like Dict[str, dict] where dict
        # is a sub-type. Patch find_validators to fix the type at use time.
        from pydantic import validators as _pv
        from pydantic import fields as _pf

        _orig_fv = _pv.find_validators

        def _patched_fv(type_, model_config):
            # If type is a function/method (not a class) but named like a builtin,
            # PEP 649 resolved it incorrectly. Use the actual builtin type instead.
            if not isinstance(type_, type) and callable(type_) and hasattr(type_, '__name__'):
                bt = _builtin_types.get(type_.__name__)
                if bt is not None:
                    type_ = bt
            return _orig_fv(type_, model_config)

        _pv.find_validators = _patched_fv
        if hasattr(_pf, 'find_validators'):
            _pf.find_validators = _patched_fv

        print("[pydantic_fix] Patched pydantic v1 for Python 3.14+")
    except Exception as _e:
        print(f"[pydantic_fix] WARNING: Could not patch pydantic: {_e}")

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
if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY") and not os.getenv("EMBEDDING_API_KEY"):
    print("WARNING: Neither OPENAI_API_KEY, DEEPSEEK_API_KEY nor EMBEDDING_API_KEY found in environment variables.")
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
import traceback
try:
    from web_app import create_app
    print("--- create_app imported successfully ---")
except Exception as e:
    print(f"FATAL: Failed to import create_app: {e}")
    traceback.print_exc()
    raise

try:
    app = create_app()
    print("--- Flask app created via factory ---")
except Exception as e:
    print(f"FATAL: Failed to create app: {e}")
    traceback.print_exc()
    raise

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Disable debug mode to prevent auto-reloading issues
    debug = False

    print(f"Starting AI Learning Path Generator on port {port}")
    print("Visit http://localhost:5000 in your browser")

    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
