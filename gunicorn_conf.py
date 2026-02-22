import multiprocessing
import os

# Gunicorn configuration for production
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Cap workers at 4 to avoid over-provisioning on smaller servers
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
keepalive = 5

# Recycle workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100  # Stagger restarts to avoid thundering herd

# Allow in-flight requests to complete during graceful reload
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Forward client IP through reverse proxy (nginx/load balancer)
forwarded_allow_ips = "*"
proxy_protocol = False
