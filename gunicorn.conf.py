import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 30
max_requests = 1000
max_requests_jitter = 50
preload_app = True
