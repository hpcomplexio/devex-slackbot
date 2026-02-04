#!/bin/bash
# Start the FAQ bot locally

set -e

# Change to project root
cd "$(dirname "$0")/.."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -e . > /dev/null

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Copy .env.example to .env and fill in your credentials"
    exit 1
fi

# Start bot
echo "Starting FAQ bot..."
python -m src.faqbot.main
