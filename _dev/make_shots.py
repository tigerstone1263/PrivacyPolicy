"""앱 캡처(1320×2868 PNG, <SCREENS_DIR>/<lang>/iphone/<화면>.png — 화면 이름은 아래 SCREENS)로
언어별 앱 화면 이미지 <앱>/assets/img/shots/<lang>/*.webp 를 만든다.

원본 비율을 자르지 않고 폭 720(히어로 두 장은 480도)으로 줄인다.
사용: python3 _dev/make_shots.py <앱 폴더 이름> <SCREENS_DIR>
  Pitch Academy: python3 _dev/make_shots.py PitchAcademy ~/abp/pitch_academy/output/store/screens
     (루트 스튜디오 페이지의 스크롤 무대도 이 화면을 쓴다)
  Absolute Ear:  python3 _dev/make_shots.py AbsoluteEar <Absolute Ear 3.0.1 캡처 폴더>
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
# 사이트 이미지 이름(템플릿 자리) → 앱마다 그 자리에 들어가는 캡처 화면 이름
SCREENS = {
    "PitchAcademy": {"phone-hero": "home", "feat-ear": "question", "feat-staff": "staff_reading",
                     "feat-create": "sing", "game-map": "map"},
    # Absolute Ear 3.0.1: 이론 연습(오선), 반복 듣기 앨범, 스테이지의 스텝 목록
    "AbsoluteEar": {"phone-hero": "home", "feat-ear": "question", "feat-staff": "theory_practice",
                    "feat-create": "repeat_listening", "game-map": "stage"},
}
SMALL = {"phone-hero", "feat-ear"}  # 첫 화면의 두 폰은 srcset 으로 480 판도 쓴다

if len(sys.argv) != 3:
    raise SystemExit(__doc__)
app, src = sys.argv[1], Path(sys.argv[2]).expanduser()
if app not in SCREENS:
    raise SystemExit(f"화면 목록이 없는 앱: {app} ({', '.join(SCREENS)})")
SHOTS = SCREENS[app]

for lang in ("ko", "en", "zh"):
    out = ROOT / app / "assets" / "img" / "shots" / lang
    out.mkdir(parents=True, exist_ok=True)
    for name, screen in SHOTS.items():
        im = Image.open(src / lang / "iphone" / f"{screen}.png").convert("RGB")
        if im.size != (1320, 2868):
            raise SystemExit(f"{lang}/{screen}.png 크기 {im.size} (1320×2868 이어야 함)")
        for width, suffix in ((720, ""), (480, "-480")):
            if suffix and name not in SMALL:
                continue
            small = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
            path = out / f"{name}{suffix}.webp"
            small.save(path, "WEBP", quality=82, method=6)
            print(f"wrote {path.relative_to(ROOT)} {small.size} {path.stat().st_size // 1000}KB")
