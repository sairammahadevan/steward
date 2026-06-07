#!/bin/bash

# STEWARD Launcher
# Double-click this file to start STEWARD and open it in your browser.

cd "$(dirname "$0")"

# Install dependencies if missing
if ! python3 -c "import anthropic" 2>/dev/null; then
    echo "Installing dependencies (first run only)..."
    pip3 install -e ".[dev]"
fi

# Open browser after a short delay
sleep 2 && open http://localhost:5001 &

echo ""
echo "=============================="
echo "  🏠 STEWARD is starting..."
echo "  Opening at http://localhost:5001"
echo "  Close this window to stop."
echo "=============================="
echo ""

PORT=5001 python3 -m src.ui.flask_app
