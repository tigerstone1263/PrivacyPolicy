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
# App Store Connect 의 provider token. ct(캠페인)는 pt 와 함께여야 집계되므로 없으면 태그를 달지 않는다.
APP_STORE_PT = None


def app_store_url(zone):
    if APP_STORE_PT:
        return f"{APP_STORE}?pt={APP_STORE_PT}&ct=homepage-{zone}"
    return APP_STORE


def play_url(zone):
    return f"{PLAY}&referrer=utm_source%3Dhomepage%26utm_medium%3Dweb%26utm_campaign%3D{zone}"


ARROW = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
         'stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>')


def roll_button(cls, href, label, aria):
    """글자가 굴러 바뀌고 화살표 칩이 도는 알약 버튼 (MotionSites text-roll). 두 번째 글자는 장식이라 aria-hidden."""
    return (f'<a class="{cls} btn-roll" href="{href}" aria-label="{aria}">'
            f'<span class="btn-roll__label"><span class="btn-roll__inner"><span>{label}</span>'
            f'<span aria-hidden="true">{label}</span></span></span>'
            f'<span class="btn-roll__chip" aria-hidden="true">{ARROW}</span></a>')


def badges(lang, s, zone):
    """스토어 버튼: 공식 배지 대신 흑백 텍스트 버튼(로고 없음 — 상표 지침상 로고는 공식 배지에서만 쓴다)."""
    apple = roll_button("store-btn store-btn--apple", app_store_url(zone), "App Store", s["badge_apple_alt"])
    play = roll_button("store-btn store-btn--play", play_url(zone), "Google Play", s["badge_play_alt"])
    return apple + play  # 모든 언어 App Store 먼저 (zh 는 spec 상 필수)


def hero_lines(title):
    """첫 화면 제목을 줄마다 blur-rise 로 차례로 올린다 (250ms 에서 시작, 줄마다 170ms 간격)."""
    lines = title.split("<br>")
    return "".join(f'<span class="in-blur h1-line" style="--d:{250 + i * 170}ms">{ln}</span>' for i, ln in enumerate(lines))


# 루트(한국어) 페이지에만 넣는 언어 안내 띠. 문구는 안내받을 사람의 언어로 쓴다.
LANG_BANNER = """<div id="lang-banner" class="lang-banner" hidden>
  <p data-for="en" lang="en">This page is also available in English. <a class="lang-banner-link" href="/en/" lang="en" data-lang="en">View in English →</a></p>
  <p data-for="zh" lang="zh-Hans">本页面也有中文版。<a class="lang-banner-link" href="/zh/" lang="zh-Hans" data-lang="zh">查看中文版 →</a></p>
  <button type="button" class="lang-banner-close" aria-label="닫기 / Close">×</button>
</div>"""


def computed(lang, s):
    return {
        "lang": lang,
        "badges_hero": badges(lang, s, "hero"),
        "badges_cta": badges(lang, s, "footer-cta"),
        "badges_try": badges(lang, s, "try"),
        "hero_lines": hero_lines(s["hero_title"]),
        "url": SITE + "/" + ("" if lang == "ko" else f"{lang}/"),
        "site": SITE,
        "shots": f"/assets/img/shots/{lang}",
        "lang_banner": LANG_BANNER if lang == "ko" else "",
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
    """세 언어를 모두 렌더링한 뒤에만 쓴다 — 하나라도 실패하면 아무 파일도 바꾸지 않는다."""
    template = (dev / "template.html").read_text(encoding="utf-8")
    pages = {}
    for lang, rel in LANGS.items():
        src = dev / "strings" / f"{lang}.json"
        if not src.exists():
            print(f"[{lang}] 문구 파일 없음: {src.name}", file=sys.stderr)
            sys.exit(1)
        strings = json.loads(src.read_text(encoding="utf-8"))
        try:
            pages[rel] = render(template, strings, computed(lang, strings))
        except KeyError as e:
            print(f"[{lang}] 문구 키 없음: {e.args[0]}", file=sys.stderr)
            sys.exit(1)
    for rel, html in pages.items():
        out = root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"wrote {rel}")


if __name__ == "__main__":
    build()
