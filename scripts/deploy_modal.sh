#!/bin/bash
# Deploy (or update) the scheduler on your Modal account. Run it yourself, once.
#   scripts/deploy_modal.sh        deploy / update
#   scripts/deploy_modal.sh off    stop it (nothing more gets posted)
# Needs: `pip install modal`, `modal setup` done once, and TELLA_API_KEY in .env
set -e
cd "$(dirname "$0")"
MODAL="${MODAL:-python3 -m modal}"
if [ "$1" = "off" ]; then $MODAL app stop tella-schedule; echo "Scheduler stopped."; exit 0; fi
KEY="$(grep '^TELLA_API_KEY=' ../.env 2>/dev/null | cut -d= -f2- | tr -d '"')"
KEY="${KEY:-$TELLA_API_KEY}"
if [ -z "$KEY" ]; then echo "Put your Tella API key in .env first:  TELLA_API_KEY=tella_pk_..."; exit 1; fi
$MODAL secret create tella-schedule TELLA_API_KEY="$KEY" --force >/dev/null
echo "Key stored as Modal secret 'tella-schedule'."
$MODAL deploy modal_app.py
echo "Scheduler is ON. It checks the queue every 10 minutes on Modal."
