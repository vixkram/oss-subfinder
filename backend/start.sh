#!/bin/bash
set -e

# Ensure we're in the right directory
cd /app

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000