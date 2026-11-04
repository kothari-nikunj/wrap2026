#!/bin/bash
# Render every slide of a wrap HTML (final state) into a contact sheet.
# usage: dev/shots.sh <wrap.html> <outdir>
set -e
HTML="$1"; OUT="$2"; C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
mkdir -p "$OUT"
NAMES=$(grep -o 'data-name="[^"]*"' "$HTML" | cut -d'"' -f2)
echo '<body style="margin:0;background:#777;display:grid;grid-template-columns:repeat(6,470px);gap:6px">' > "$OUT/sheet.html"
for n in $NAMES; do
  "$C" --headless=new --hide-scrollbars --window-size=1280,860 --virtual-time-budget=4000 --screenshot="$OUT/$n.png" "file://$HTML?still#$n" 2>/dev/null
  sips -c 860 470 "$OUT/$n.png" --out "$OUT/c_$n.png" >/dev/null 2>&1
  echo "<img src=\"c_$n.png\">" >> "$OUT/sheet.html"
done
COUNT=$(echo "$NAMES" | wc -w); ROWS=$(( (COUNT + 5) / 6 ))
"$C" --headless=new --hide-scrollbars --window-size=2850,$((ROWS * 866)) --screenshot="$OUT/sheet.png" "file://$OUT/sheet.html" 2>/dev/null
echo "$OUT/sheet.png ($COUNT slides)"
