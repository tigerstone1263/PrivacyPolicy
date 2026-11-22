#!/usr/bin/env bash
# 페이지 묶음(루트·앱 폴더) × 3개 언어 × 360/768/1280 폭 전체 페이지 PNG (+ 360px 글꼴 115%) 를 OUT 폴더에 저장한다.
# 사용: _dev/screenshot.sh OUT_DIR [묶음...]   묶음: root PitchAcademy AbsoluteEar (기본: 모두)
#   저장소 루트에서 python3 -m http.server $PORT(기본 8765) 실행 중이어야 함
set -euo pipefail
OUT=${1:?OUT_DIR}; shift
GROUPS_=${*:-root PitchAcademy AbsoluteEar}
PORT=${PORT:-8765}
mkdir -p "$OUT"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
shot() { # name width height path scale
  local prof; prof=$(mktemp -d)
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=6000 --user-data-dir="$prof" \
    --window-size="$(( $2 + 40 )),$3" --screenshot="$OUT/$1.png" \
    "http://127.0.0.1:$PORT/_dev/frame.html?w=$2&h=$3&p=$4&scale=$5" >/dev/null 2>&1 || true
  rm -rf "$prof"
}
for g in $GROUPS_; do
  base=/$g/; [ "$g" = root ] && base=/
  for lang in ko en zh; do
    p=$base; [ "$lang" != ko ] && p=$base$lang/
    shot "$g-$lang-360" 360 9800 "$p" 1
    shot "$g-$lang-360x115" 360 11000 "$p" 1.15
    shot "$g-$lang-768" 768 7600 "$p" 1
    shot "$g-$lang-1280" 1280 6600 "$p" 1
  done
done
echo "saved to $OUT"
