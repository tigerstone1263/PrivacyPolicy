"""스토어 캡처(absolute_ear 저장소의 output/store/screens/<lang>/iphone/*.png)로
언어별 앱 화면 이미지 AbsoluteEar/assets/img/shots/<lang>/*.webp 를 만든다(루트 페이지도 같은 것을 쓴다).

원본 1320×2868 비율을 자르지 않고 폭 720(히어로 두 장은 480도)으로 줄인다.
사용: python3 _dev/make_shots.py [SCREENS_DIR]
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    Path.home() / "abp" / "absolute_ear-store-assets" / "output" / "store" / "screens"
# 사이트 이미지 이름 → 스토어 화면 이름
SHOTS = {"phone-hero": "home", "feat-ear": "question", "feat-staff": "staff_reading",
         "feat-create": "sing", "game-map": "map"}
SMALL = {"phone-hero", "feat-ear"}  # 첫 화면의 두 폰은 srcset 으로 480 판도 쓴다

for lang in ("ko", "en", "zh"):
    out = ROOT / "AbsoluteEar" / "assets" / "img" / "shots" / lang
    out.mkdir(parents=True, exist_ok=True)
    for name, screen in SHOTS.items():
        im = Image.open(SRC / lang / "iphone" / f"{screen}.png").convert("RGB")
        if im.size != (1320, 2868):
            raise SystemExit(f"{lang}/{screen}.png 크기 {im.size} (1320×2868 이어야 함)")
        for width, suffix in ((720, ""), (480, "-480")):
            if suffix and name not in SMALL:
                continue
            small = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
            path = out / f"{name}{suffix}.webp"
            small.save(path, "WEBP", quality=82, method=6)
            print(f"wrote {path.relative_to(ROOT)} {small.size} {path.stat().st_size // 1000}KB")
