#!/bin/bash
set -e

# Ensure we're in the backend directory inside the container
cd /app/backend

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
