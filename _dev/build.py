"""strings/<lang>.json 을 template.html 에 채워 언어별 index.html 을 만든다.

템플릿의 {{key}} 는 문구 JSON 값으로, {{@name}} 은 아래 계산값으로 채운다.
JSON 에 없는 키가 템플릿에 있으면 KeyError 로 빌드를 멈춘다.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEV = ROOT / "_dev"
LANGS = {"ko": "index.html", "en": "en/index.html", "zh": "zh/index.html"}
SITE = "https://tigerstone1263.com"
APP_STORE = "https://apps.apple.com/app/id6739764701"
PLAY = "https://play.google.com/store/apps/details?id=com.tigerstone.AbsoluteEar"


def app_store_url(zone):
    return f"{APP_STORE}?ct=homepage-{zone}"


def play_url(zone):
    return f"{PLAY}&referrer=utm_source%3Dhomepage%26utm_medium%3D{zone}"


def svg_width(path, height):
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', path.read_text(encoding="utf-8"))
    return round(float(m.group(1)) / float(m.group(2)) * height)


def png_width(path, height):
    import struct
    w, h = struct.unpack(">II", path.read_bytes()[16:24])
    return round(w / h * height)


def badges(lang, s, zone):
    aw = svg_width(ROOT / "assets" / "badges" / f"appstore-{lang}.svg", 48)
    pw = png_width(ROOT / "assets" / "badges" / f"play-{lang}.png", 48)
    apple = (
        f'<a class="badge badge-apple" href="{app_store_url(zone)}">'
        f'<img src="/assets/badges/appstore-{lang}.svg" alt="{s["badge_apple_alt"]}" width="{aw}" height="48"></a>'
    )
    play = (
        f'<a class="badge badge-play" href="{play_url(zone)}">'
        f'<img src="/assets/badges/play-{lang}.png" alt="{s["badge_play_alt"]}" width="{pw}" height="48"></a>'
    )
    return apple + play  # 모든 언어 App Store 먼저 (zh 는 spec 상 필수)


def computed(lang, s):
    return {
        "lang": lang,
        "badges_hero": badges(lang, s, "hero"),
        "badges_cta": badges(lang, s, "footer-cta"),
        "url": SITE + "/" + ("" if lang == "ko" else f"{lang}/"),
        "site": SITE,
        **{f"cur_{l}": 'aria-current="true"' if l == lang else "" for l in LANGS},
    }


def render(template, strings, calc):
    def sub(m):
        key = m.group(1)
        if key.startswith("@"):
            return calc[key[1:]]
        return strings[key]

    return re.sub(r"\{\{\s*(@?[\w.-]+)\s*\}\}", sub, template)


def build(dev=DEV, root=ROOT):
    template = (dev / "template.html").read_text(encoding="utf-8")
    for lang, rel in LANGS.items():
        src = dev / "strings" / f"{lang}.json"
        if not src.exists():
            continue
        strings = json.loads(src.read_text(encoding="utf-8"))
        try:
            html = render(template, strings, computed(lang, strings))
        except KeyError as e:
            print(f"[{lang}] 문구 키 없음: {e.args[0]}", file=sys.stderr)
            sys.exit(1)
        out = root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"wrote {rel}")


if __name__ == "__main__":
    build()
