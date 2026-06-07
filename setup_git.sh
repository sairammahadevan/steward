#!/usr/bin/env bash
# Run this once from your Mac Terminal inside the steward folder:
#   cd ~/projects/steward && bash setup_git.sh
#
# Before running: create a repo on github.com (empty, no README)
# Then set your repo URL below:

GITHUB_REPO="https://github.com/sairammahadevan/steward.git"

set -e
cd "$(dirname "$0")"

echo "→ Cleaning up any stale git locks..."
rm -f .git/index.lock

echo "→ Configuring git..."
git config user.email "sairammahadevan@gmail.com"
git config user.name "Sairam Mahadevan"
git branch -m main 2>/dev/null || true

echo "→ Committing all files..."
git commit -m "Initial commit: STEWARD v0.1.0

Personal home document management system.

Features:
- PDF ingestion (text + scanned via Claude vision)
- Background processing with real-time progress tracking
- Multi-turn conversational Q&A (Ask page)
- Email-to-ingest via Gmail IMAP + APScheduler
- Re-ingest with higher quality (Sonnet + 150 DPI)
- Token and file size tracking per document
- Document search, grouping, status management
- Local-first: Flask + SQLite, no cloud storage"

echo "→ Adding remote..."
git remote add origin "$GITHUB_REPO"

echo "→ Pushing to GitHub..."
git push -u origin main

echo ""
echo "✅ Done! Your code is live at: $GITHUB_REPO"
