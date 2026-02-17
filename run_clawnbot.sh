#!/bin/bash
# run_clawnbot.sh - Wrapper to run the bot with .env

# Source the .env file from clawd directory
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo "⚠️ .env dosyası bulunamadı, environment variables eksik olabilir."
fi

# Activate venv and run
echo "🤖 Clawnbot başlatılıyor..."
./.venv/bin/python clawnbot.py
