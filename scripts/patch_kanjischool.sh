#!/bin/bash

DIST_DIR="/home/tra01/project/hanachan-v2/kanjischool/dist"

if [ ! -d "$DIST_DIR" ]; then
  echo "Error: Dist directory not found at $DIST_DIR"
  exit 1
fi

echo "Patching KanjiSchool dist files to point to local Hanachan API (using absolute origin)..."

# Find all .js and .css files in dist/assets
# Replace 'https://api.wanikani.com/v2' (quoted) with JS expression window.location.origin + "/v2"
# We handle both double and single quotes
find "$DIST_DIR" -type f \( -name "*.js" -o -name "*.css" -o -name "*.html" \) -exec sed -i 's|"https://api.wanikani.com/v2"|(window.location.origin+"/v2")|g' {} +
find "$DIST_DIR" -type f \( -name "*.js" -o -name "*.css" -o -name "*.html" \) -exec sed -i "s|'https://api.wanikani.com/v2'|(window.location.origin+'/v2')|g" {} +

# Fail-safe for any remaining unquoted occurrences (though unlikely to be problematic for URL constructor)
find "$DIST_DIR" -type f \( -name "*.js" -o -name "*.css" -o -name "*.html" \) -exec sed -i "s|https://api.wanikani.com/v2|/v2|g" {} +

echo "Patching complete. URL constructor issue resolved by using absolute location.origin."
