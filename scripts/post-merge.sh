#!/bin/bash
# Post-merge setup for the AIRWORTHY / Rentalizer workspace.
#
# The app's Python dependencies are managed by the Replit uv project at the
# workspace root (pyproject.toml + uv.lock). Task merges may add or upgrade
# packages, which are recorded there. `uv sync` reconciles the installed
# environment with the lockfile so the merged code has exactly the deps it
# expects. It is fast and idempotent.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "post-merge: syncing Python environment from uv.lock..."
uv sync

echo "post-merge: done."
