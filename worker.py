import os
import sys

# Fix pydantic v1 for Python 3.14+ (must be before any pydantic/langchain import)
if sys.version_info >= (3, 14):
    try:
        from pydantic.main import ModelMetaclass as _MC
        import builtins as _builtins
        _builtin_types = {
            name: obj for name, obj in vars(_builtins).items()
            if isinstance(obj, type)
        }
        _orig_mc_new = _MC.__new__
        def _patched_mc_new(mcs, name, bases, namespace, **kwargs):
            if '__annotations__' not in namespace and '__annotate_func__' in namespace:
                try:
                    ann = namespace['__annotate_func__'](1)
                    for key, value in ann.items():
                        if not isinstance(value, type) and callable(value) and hasattr(value, '__name__'):
                            if value.__name__ in _builtin_types:
                                ann[key] = _builtin_types[value.__name__]
                    namespace['__annotations__'] = ann
                except Exception:
                    pass
            return _orig_mc_new(mcs, name, bases, namespace, **kwargs)
        _MC.__new__ = staticmethod(_patched_mc_new)
    except Exception:
        pass

import redis
from rq import Worker, Queue, Connection
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

listen = ['learning-paths']

redis_url = os.getenv('REDIS_URL')
if not redis_url:
    raise RuntimeError("REDIS_URL environment variable not set.")

# Establish Redis connection
# Only pass ssl_cert_reqs for TLS endpoints
if redis_url.startswith('rediss://'):
    conn = redis.from_url(redis_url, ssl_cert_reqs=None)
else:
    conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        print(f"Starting RQ worker, listening on queues: {', '.join(listen)}...")
        worker = Worker(map(Queue, listen))
        worker.work()
