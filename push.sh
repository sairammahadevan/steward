#!/usr/bin/env bash
# Run from Terminal: cd ~/projects/steward && bash push.sh
set -e
cd "$(dirname "$0")"

git add -A
git commit -m "UI redesign + email subject filter + docs

UI:
- Warm Intelligence design system (style.css full rewrite)
- Sidebar: coral/amber S logomark, left-border active indicator
- Stat cards: 3px gradient top borders per type
- Chat bubbles: indigo gradient user, white card Claude with S avatar
- marked.js markdown rendering in chat responses
- Topbar title 18px DM Sans, subtitle darker text-2
- Body text colors darkened (--text-2 #3D3A35, --text-3 #7C7670)
- About + Architecture page text fixed (was light grey)
- DM Sans font for headings and stat numbers

Features:
- Email ingest: filter by subject STEWARD (prevents normal inbox ingestion)

Docs:
- docs/BUSINESS.md: product context, features, roadmap
- docs/TECH.md: stack, file structure, routes, env vars, design system
- docs/ARCHITECTURE.md: system diagram, pipelines, ADRs, DB schema, concurrency"

git push origin main
echo ""
echo "✅ Pushed to https://github.com/sairammahadevan/steward"
