#!/usr/bin/env bash
set -e

# Create docs folder if it doesn't exist
mkdir -p docs

# Install dependencies if needed
if ! python3 -c "import anthropic" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install -e ".[dev]"
fi

echo "Starting STEWARD at http://localhost:5001"
PORT=${PORT:-5001} python3 -m src.ui.flask_app
