#!/bin/bash
#!/bin/bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker vicky_app:app --bind 0.0.0.0:$PORT