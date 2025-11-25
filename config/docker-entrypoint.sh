#!/bin/bash
set -e

# Ensure templates directory exists and is writable
mkdir -p /app/templates
chmod 755 /app/templates

# Copy initial templates if templates directory is empty
if [ ! "$(ls -A /app/templates)" ]; then
    echo "Initializing templates directory..."
    if [ -d "/tmp/templates_source" ]; then
        cp -r /tmp/templates_source/* /app/templates/
    fi
fi

# Execute the main command
exec "$@"
