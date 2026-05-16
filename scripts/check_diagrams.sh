#!/usr/bin/env bash
# Validate every Mermaid block in docs/ renders via mmdc.
set -euo pipefail

MMDC="${MMDC:-pnpm exec mmdc}"
PUPPETEER_CFG="${PUPPETEER_CFG:-$(dirname "$0")/puppeteer-config.json}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail=0
i=0

# Extract every fenced ```mermaid block into a tmp file.
# Sanitize doc paths to flat filenames so multiple diagrams from the same doc don't collide.
while IFS= read -r doc; do
  awk -v base="$TMP" -v doc="$doc" '
    /^```mermaid$/ {
      inblock=1
      idx++
      flat=doc
      gsub("[/\\\\]", "_", flat)
      outfile=sprintf("%s/%s.%03d.mmd", base, flat, idx)
      next
    }
    /^```$/ && inblock { inblock=0; next }
    inblock { print >> outfile }
  ' "$doc"
done < <(find docs -type f -name "*.md")

shopt -s nullglob
for mmd in "$TMP"/*.mmd; do
  i=$((i+1))
  out="${mmd%.mmd}.svg"
  err="$(${MMDC} -i "$mmd" -o "$out" -p "$PUPPETEER_CFG" -q 2>&1)" || {
    echo "diagram failed to render: $mmd"
    echo "----- stderr -----"
    echo "$err"
    echo "----- source -----"
    cat "$mmd"
    echo "------------------"
    fail=1
  }
done

echo "checked $i diagram(s)"
exit "$fail"
