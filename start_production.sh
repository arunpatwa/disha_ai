#!/bin/bash
# Production startup script for Render/Railway/etc

# Initialize database if needed
if [ ! -f "disha_ai.db" ]; then
    echo "Initializing database..."
    python init_db.py
fi

# Start the server
echo "Starting Disha AI server..."
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
