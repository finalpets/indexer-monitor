#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "→ Pulling latest changes..."
git pull

echo "→ Building image..."
docker build -t indexer-monitor .

echo "→ Recreating container..."
docker rm -f indexer-monitor 2>/dev/null || true
docker run -d \
  --name indexer-monitor \
  --restart unless-stopped \
  -v "$(pwd)/data:/app/data" \
  indexer-monitor

echo "✓ Done. Logs:"
docker logs --tail 20 indexer-monitor
