#!/bin/bash
# Dashboard for an EC2 GPU instance. Batch jobs keep using entrypoint.sh.
set -euo pipefail
export MC_HOST="${MC_HOST:-0.0.0.0}"
export MC_PORT="${MC_PORT:-8765}"
export MC_ENGINE="${MC_ENGINE:-/opt/mc_engine}"
exec python3 /opt/dashboard/server.py
