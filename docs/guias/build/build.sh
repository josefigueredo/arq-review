#!/usr/bin/env bash
# Regenerates the standalone HTML version of each guide from its Markdown (the source).
# Needs pandoc and mmdc (Mermaid CLI). Usage: docs/guias/build/build.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
guias="$(dirname "$here")"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
for md in "$guias"/*.md; do
  name="$(basename "$md" .md)"
  # Mermaid blocks → SVG files referenced from a copy of the Markdown
  mmdc -q -i "$md" -o "$tmp/$name.md" -e svg -b transparent -c "$here/mermaid.json" >/dev/null
  title="$(sed -n '1s/^# //p' "$md")"
  (cd "$tmp" && pandoc "$name.md" -f gfm -t html5 --standalone --embed-resources \
    --template "$here/template.html" --toc --toc-depth=3 --lua-filter "$here/md-links.lua" \
    --metadata title="$title" -o "$guias/$name.html")
  echo "ok: docs/guias/$name.html"
done
