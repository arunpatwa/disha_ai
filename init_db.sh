#!/bin/bash

# Initialize database script

echo "Initializing Disha AI database..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your API keys before running the application"
fi

# Create database if it doesn't exist
echo "Creating PostgreSQL database..."

# Extract database name from DATABASE_URL
DB_NAME="disha_ai"

# Create database (will fail if exists, which is fine)
createdb $DB_NAME 2>/dev/null || echo "Database $DB_NAME already exists"

# Run the application to create tables
echo "Creating database tables..."
python3 << END
from database import engine, Base
from models import User, Message, Memory, Protocol, TypingIndicator

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("✓ Tables created successfully")

# Seed protocols
from database import SessionLocal
from services import ProtocolService

db = SessionLocal()
try:
    print("Seeding default protocols...")
    ProtocolService.seed_default_protocols(db)
    print("✓ Protocols seeded successfully")
finally:
    db.close()

END

echo ""
echo "✓ Database initialized successfully!"
echo ""
echo "Next steps:"
echo "1. Update .env with your API keys"
echo "2. Run: python main.py"
echo "3. Open http://localhost:8000 in your browser"
