import os
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
# The ssl_cert_reqs=None is used for services like Upstash that use self-signed certs.
# For other Redis providers, you might remove this.
conn = redis.from_url(redis_url, ssl_cert_reqs=None)

if __name__ == '__main__':
    with Connection(conn):
        print(f"Starting RQ worker, listening on queues: {', '.join(listen)}...")
        worker = Worker(map(Queue, listen))
        worker.work()
