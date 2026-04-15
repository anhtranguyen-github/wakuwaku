#!/bin/bash

DIST_DIR="/home/tra01/project/hanachan-v2/kanjischool/dist"

if [ ! -d "$DIST_DIR" ]; then
  echo "Error: Dist directory not found at $DIST_DIR"
  exit 1
fi

echo "Patching KanjiSchool dist files to point to local Hanachan API..."

# Find all .js and .css files in dist/assets
# Replace 'https://api.wanikani.com/v2' with '/v2' (handled by frontend server proxy)
find "$DIST_DIR" -type f \( -name "*.js" -o -name "*.css" -o -name "*.html" \) -exec sed -i "s|https://api.wanikani.com/v2|/v2|g" {} +

echo "Patching complete. API calls now directed to relative /v2 (proxied to port 7000)"
