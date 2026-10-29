#!/usr/bin/env bash
# 3개 언어 × 360/768/1280 폭 전체 페이지 PNG (+ 360px 글꼴 115%) 를 OUT 폴더에 저장한다.
# 사용: _dev/screenshot.sh OUT_DIR   (저장소 루트에서 python3 -m http.server 8765 실행 중이어야 함)
set -euo pipefail
OUT=${1:?OUT_DIR}
mkdir -p "$OUT"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
shot() { # name width height path scale
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=6000 \
    --window-size="$(( $2 + 40 )),$3" --screenshot="$OUT/$1.png" \
    "http://localhost:8765/_dev/frame.html?w=$2&h=$3&p=$4&scale=$5" >/dev/null 2>&1
}
for lang in ko en zh; do
  p=/; [ "$lang" != ko ] && p=/$lang/
  shot "$lang-360" 360 9800 "$p" 1
  shot "$lang-360x115" 360 11000 "$p" 1.15
  shot "$lang-768" 768 7600 "$p" 1
  shot "$lang-1280" 1280 6600 "$p" 1
done
echo "saved to $OUT"
