#!/bin/bash

# Quick start script for Disha AI

set -e  # Exit on error

echo "=========================================="
echo "  Disha AI - Quick Start"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "⚠️  Warning: Python 3.10+ recommended (found $python_version)"
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env and add your API keys!"
    echo ""
    echo "Required settings:"
    echo "  1. DATABASE_URL (if not using default)"
    echo "  2. OPENAI_API_KEY or ANTHROPIC_API_KEY"
    echo ""
    read -p "Press Enter to edit .env now, or Ctrl+C to exit and edit later..."
    ${EDITOR:-nano} .env
fi

# Check if database exists
echo ""
echo "Checking database..."
if ! psql -lqt | cut -d \| -f 1 | grep -qw disha_ai; then
    echo "Database doesn't exist. Creating..."
    createdb disha_ai 2>/dev/null || true
fi

# Initialize database
echo ""
echo "Initializing database..."
python init_db.py

echo ""
echo "=========================================="
echo "  ✓ Setup Complete!"
echo "=========================================="
echo ""
echo "To start the application:"
echo "  python main.py"
echo ""
echo "Then open: http://localhost:8000"
echo ""
echo "To run tests:"
echo "  python test_api.py"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo ""

# Ask if user wants to start now
read -p "Start the application now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting Disha AI..."
    echo "Press Ctrl+C to stop"
    echo ""
    python main.py
fi
