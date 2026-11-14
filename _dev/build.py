"""문구 JSON 을 템플릿에 채워 페이지 묶음(앱 폴더·루트)마다 언어별 index.html 을 만든다.

템플릿의 {{key}} 는 문구 JSON 값으로, {{@name}} 은 아래 계산값으로 채운다.
JSON 에 없는 키가 템플릿에 있으면 KeyError 로 빌드를 멈춘다.
같이 만드는 것: 앱 폴더의 정책 페이지(_dev/policy 원본 복사), 옛 /get/ 사본, sitemap.xml, 404.html(대소문자 틀린 주소 구제).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEV = ROOT / "_dev"
LANGS = ("ko", "en", "zh")
HREFLANG = {"ko": "ko", "en": "en", "zh": "zh-Hans"}
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


# 묶음의 한국어 페이지에만 넣는 언어 안내 띠. 문구는 안내받을 사람의 언어로 쓴다.
LANG_BANNER = """<div id="lang-banner" class="lang-banner" hidden>
  <p data-for="en" lang="en">This page is also available in English. <a class="lang-banner-link" href="{base}en/" lang="en" data-lang="en">View in English →</a></p>
  <p data-for="zh" lang="zh-Hans">本页面也有中文版。<a class="lang-banner-link" href="{base}zh/" lang="zh-Hans" data-lang="zh">查看中文版 →</a></p>
  <button type="button" class="lang-banner-close" aria-label="닫기 / Close">×</button>
</div>"""


# 페이지 묶음. base 는 주소 앞부분, assets 는 그 묶음 전용 에셋 폴더(주소).
APP = {
    "name": "AbsoluteEar",
    "base": "/AbsoluteEar/",
    "assets": "/AbsoluteEar/assets",
    "shots": "/AbsoluteEar/assets/img/shots",
    "template": DEV / "template.html",
    "strings": DEV / "strings",
}
# 루트: TigerStone1263 스튜디오 페이지. 앱 화면은 앱 폴더의 언어별 캡처를 그대로 쓴다.
STUDIO = {
    "name": "TigerStone1263",
    "base": "/",
    "assets": "/assets",
    "shots": "/AbsoluteEar/assets/img/shots",
    "template": DEV / "studio" / "template.html",
    "strings": DEV / "studio" / "strings",
}
GROUPS = [STUDIO, APP]

# 스토어에 등록된 루트 정책 파일은 바이트 하나도 바꾸지 않는다(policy_hashes.json) — 옛 앱 버전과 스토어 등록이 그 주소를 연다.
# 앱 폴더의 정책 주소는 _dev/policy 의 원본을 바이트 그대로 복사한다. 내용은 원본에서 고치고 빌드한다.
# (_dev 는 GitHub Pages(Jekyll)가 내보내지 않으므로 원본 주소는 공개되지 않는다)
POLICY_PAGES = {
    "AbsoluteEar/PrivacyPolicy.html": DEV / "policy" / "PrivacyPolicy.html",
    "AbsoluteEar/TermsOfService.html": DEV / "policy" / "TermsOfService.html",
    # Pitch Academy 는 아직 소개 페이지 없이 정책 두 쪽만 둔다(스토어 등록에 적는 주소)
    "PitchAcademy/PrivacyPolicy.html": DEV / "policy" / "PitchAcademy" / "PrivacyPolicy.html",
    "PitchAcademy/TermsOfService.html": DEV / "policy" / "PitchAcademy" / "TermsOfService.html",
}
# 원본에 남은 소유자 결정 자리. 게시 전에 모두 채운다(check_site.py --publish 가 막는다)
POLICY_PLACEHOLDER = "[OWNER DECISION"
# 옛 QR 주소(/get/)는 앱 폴더 것과 같은 내용으로 둔다 — 한 번 더 이동시키지 않으려고.
GET_COPY = ("AbsoluteEar/get/index.html", "get/index.html")
# 404 구제 대상이 되는, 페이지 묶음 밖의 정식 주소
EXTRA_PATHS = ["/AbsoluteEar/get/", "/get/", "/AbsoluteEar/PrivacyPolicy", "/AbsoluteEar/TermsOfService",
               "/PitchAcademy/PrivacyPolicy", "/PitchAcademy/TermsOfService",
               "/AbsoluteEarPolicy.html", "/termsOfService.html", "/privacyPolicy.html", "/PitchRunner.html"]


def lang_path(base, lang):
    return base if lang == "ko" else f"{base}{lang}/"


def out_file(base, lang):
    return lang_path(base, lang).lstrip("/") + "index.html"


def alternates(base):
    rows = [(HREFLANG[l], SITE + lang_path(base, l)) for l in LANGS] + [("x-default", SITE + base)]
    return "\n".join(f'<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in rows)


def computed(lang, s, g):
    base, a = g["base"], g["assets"]
    return {
        "lang": lang,
        "base": base,
        "a": a,
        "badges_hero": badges(lang, s, "hero"),
        "badges_cta": badges(lang, s, "footer-cta"),
        "badges_try": badges(lang, s, "try"),
        "badges_studio": badges(lang, s, "studio"),
        "hero_lines": hero_lines(s["hero_title"]) if "hero_title" in s else "",
        "app_lang_path": "" if lang == "ko" else f"{lang}/",
        "url": SITE + lang_path(base, lang),
        "alternates": alternates(base),
        "site": SITE,
        "shots": f"{g['shots']}/{lang}",
        "lang_banner": LANG_BANNER.format(base=base) if lang == "ko" else "",
        **{f"cur_{l}": 'aria-current="true"' if l == lang else "" for l in LANGS},
    }


def render(template, strings, calc):
    def sub(m):
        key = m.group(1)
        if key.startswith("@"):
            return calc[key[1:]]
        return strings[key]

    return re.sub(r"\{\{\s*(@?[\w.-]+)\s*\}\}", sub, template)


def sitemap(groups):
    urls = []
    for g in groups:
        alts = [(HREFLANG[l], SITE + lang_path(g["base"], l)) for l in LANGS] + [("x-default", SITE + g["base"])]
        links = "\n".join(f'    <xhtml:link rel="alternate" hreflang="{h}" href="{u}"/>' for h, u in alts)
        for l in LANGS:
            urls.append(f"  <url>\n    <loc>{SITE + lang_path(g['base'], l)}</loc>\n{links}\n  </url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(urls) + "\n</urlset>\n")


def known_paths(groups):
    return [lang_path(g["base"], l) for g in groups for l in LANGS] + EXTRA_PATHS


# GitHub Pages 는 주소의 대소문자를 구분한다(/absoluteear → 404). 맥은 대소문자만 다른 폴더를 둘 수 없으므로
# 404 페이지에서 알려진 정식 주소로 보낸다. 비교 키: 소문자, .html·index.html·끝 / 를 뗀 것.
NOT_FOUND = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>404 · TigerStone1263</title>
<link rel="icon" type="image/png" href="/favicon.png">
<script>
(function () {
  var KNOWN = __KNOWN__;
  function key(p) { return p.toLowerCase().replace(/\\/index\\.html$/, '/').replace(/\\.html$/, '').replace(/\\/+$/, ''); }
  var here, to = null;
  try { here = key(decodeURI(location.pathname)); } catch (e) { here = key(location.pathname); }
  for (var i = 0; i < KNOWN.length && !to; i++) if (key(KNOWN[i]) === here) to = KNOWN[i];
  if (!to) {  // 앱 폴더 안의 모르는 주소는 그 앱 첫 화면으로(첫 화면이 있는 앱만 — 정책 쪽만 있는 앱은 보낼 곳이 없다)
    var seg = here.split('/')[1] || '';
    for (var j = 0; j < KNOWN.length && !to; j++) {
      var top = KNOWN[j].split('/')[1] || '';
      if (top && KNOWN[j] === '/' + top + '/' && top.toLowerCase() === seg) to = KNOWN[j];
    }
  }
  if (to && to !== location.pathname) location.replace(to + location.search + location.hash);
})();
</script>
<style>
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #fafafa; color: #191919;
         font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif; text-align: center; }
  h1 { font-size: 3rem; margin: 0 0 12px; letter-spacing: -0.03em; }
  p { margin: 6px 0; color: #6b6b6b; }
  a { color: #191919; font-weight: 700; }
</style>
</head>
<body>
<main>
  <h1>404</h1>
  <p>페이지를 찾을 수 없어요.</p>
  <p lang="en">Page not found.</p>
  <p lang="zh-Hans">找不到该页面。</p>
  <p><a href="/">tigerstone1263.com</a></p>
</main>
</body>
</html>
"""


def build(dev=DEV, root=ROOT):
    """모든 파일을 메모리에서 만든 뒤에만 쓴다 — 하나라도 실패하면 아무 파일도 바꾸지 않는다."""
    out = {}
    for g in GROUPS:
        tpl_path = dev / g["template"].relative_to(DEV)
        str_dir = dev / g["strings"].relative_to(DEV)
        template = tpl_path.read_text(encoding="utf-8")
        for lang in LANGS:
            src = str_dir / f"{lang}.json"
            if not src.exists():
                print(f"[{g['name']}/{lang}] 문구 파일 없음: {src.name}", file=sys.stderr)
                sys.exit(1)
            strings = json.loads(src.read_text(encoding="utf-8"))
            try:
                out[out_file(g["base"], lang)] = render(template, strings, computed(lang, strings, g))
            except KeyError as e:
                print(f"[{g['name']}/{lang}] 문구 키 없음: {e.args[0]}", file=sys.stderr)
                sys.exit(1)
    for dst, src in POLICY_PAGES.items():
        src = dev / src.relative_to(DEV)
        if not src.exists():
            print(f"[{dst}] 정책 원본 없음: _dev/{src.relative_to(dev).as_posix()}", file=sys.stderr)
            sys.exit(1)
        out[dst] = src.read_bytes()  # 바이트 그대로(줄바꿈·인코딩을 건드리지 않는다)
    out[GET_COPY[1]] = (root / GET_COPY[0]).read_text(encoding="utf-8")
    out["sitemap.xml"] = sitemap(GROUPS)
    out["404.html"] = NOT_FOUND.replace("__KNOWN__", json.dumps(known_paths(GROUPS)))
    for rel, text in out.items():
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            f.write_bytes(text)
        else:
            f.write_text(text, encoding="utf-8")
        print(f"wrote {rel}")


if __name__ == "__main__":
    build()
