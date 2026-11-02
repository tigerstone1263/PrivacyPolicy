"""홈페이지 정적 검사. 통과하면 OK, 실패하면 이유를 출력하고 exit 1."""
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEV = ROOT / "_dev"
sys.dont_write_bytecode = True  # _dev/__pycache__ 가 저장소에 끼지 않게
sys.path.insert(0, str(DEV))
import build  # noqa: E402  주소 규칙(GROUPS·POLICY_COPIES·known_paths)을 빌드와 같은 곳에서 읽는다

SITE = "https://tigerstone1263.com"
AE_BASE = "/AbsoluteEar/"
A = "/AbsoluteEar/assets"            # AE 전용 에셋 주소
AE_ASSETS = ROOT / "AbsoluteEar" / "assets"
CSS = AE_ASSETS / "css" / "site.css"
PAGES = {"ko": "AbsoluteEar/index.html", "en": "AbsoluteEar/en/index.html", "zh": "AbsoluteEar/zh/index.html"}
STUDIO_PAGES = {"ko": "index.html", "en": "en/index.html", "zh": "zh/index.html"}
STUDIO_CSS = ROOT / "assets" / "css" / "studio.css"

APP_STORE = "apps.apple.com/app/id6739764701"
PLAY = "id=com.tigerstone.AbsoluteEar"
FORBIDDEN_TEXT = ["나리", "₩", "$", "원/월"]
# 앱 동작보다 과장되거나 앱 화면 용어와 다른 표현
FORBIDDEN_BY_LANG = {
    "ko": ["바로 열기", "하트 없이 열어요", "계정을 연동", "원하는 곡을 반복", "진도를 나눠", "박자를 듣고 맞히는", "코드 진행", "걱정 없이 광고 없이"],
    "en": ["Unlock the next chapter", "Music mode", "Made for", "pieces you choose", "share progress", "hear and match the beat"],
    "zh": ["直接解锁下一章", "反复听播放列表", "想听的曲子", "分享进度", "对节奏"],
}

errors = []


def fail(msg):
    errors.append(msg)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []  # (href, attrs)
        self.scripts = []
        self.text = []
        self.attrs_all = []
        self.title_text = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.attrs_all.append((tag, a))
        if tag == "a":
            self.links.append(a.get("href", ""))
        if tag == "script":
            self.scripts.append(a.get("src"))
        if tag in ("script", "style"):
            self._skip += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in ("script", "style"):
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title_text.append(data)
        if not self._skip:
            self.text.append(data)


def parse(path):
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    return p


def check_policy_files():
    hashes = json.loads((DEV / "policy_hashes.json").read_text())
    for name, digest in hashes.items():
        f = ROOT / name
        if not f.exists():
            fail(f"정책 파일 없음: {name}")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != digest:
            fail(f"정책 파일이 바뀜: {name}")


def check_page(lang, rel):
    path = ROOT / rel
    if not path.exists():
        fail(f"[{lang}] {rel} 없음")
        return None
    p = parse(path)
    links = p.links
    # App Store 는 pt(provider token)가 있을 때만 구역 태그를 단다 (build.APP_STORE_PT)
    tagged = [(PLAY, "Google Play")] + ([(APP_STORE, "App Store")] if any("pt=" in h for h in links) else [])
    for store, label in tagged:
        for zone in ("hero", "footer-cta"):
            if not any(store in h and zone in h for h in links):
                fail(f"[{lang}] {label} 링크에 {zone} 태그 없음")
    if sum(APP_STORE in h for h in links) < 2:
        fail(f"[{lang}] App Store 링크가 히어로·마지막 구역에 모두 있어야 함")
    for h in links:
        if APP_STORE in h and "ct=" in h and "pt=" not in h:
            fail(f"[{lang}] App Store ct 는 pt 없이 집계되지 않음: {h}")
        if PLAY in h and "utm_campaign%3D" not in h:
            fail(f"[{lang}] Play 링크에 utm_campaign 없음: {h}")
    for h in links:
        if h.startswith("javascript:"):
            fail(f"[{lang}] JS 링크 사용: {h}")
    for need in ("/AbsoluteEar/PrivacyPolicy", "/AbsoluteEar/TermsOfService", "mailto:tigerstone1263@gmail.com"):
        if need not in links:
            fail(f"[{lang}] 링크 없음: {need}")
    if any("privacyPolicy.html" in h for h in links):
        fail(f"[{lang}] 다른 앱 정책(privacyPolicy.html) 링크됨")
    text = "".join(p.text)
    for w in FORBIDDEN_TEXT + FORBIDDEN_BY_LANG[lang]:
        if w in text:
            fail(f"[{lang}] 금지 문자열 포함: {w}")
    for src in p.scripts:
        if src and src.startswith(("http:", "https:", "//")):
            fail(f"[{lang}] 외부 스크립트: {src}")
    if "Google Play" not in text or "Google LLC" not in text or "Apple Inc." not in text:
        fail(f"[{lang}] 스토어 상표 고지 없음")
    navs = [a for t, a in p.attrs_all if t == "nav"]
    if any(not a.get("aria-label") for a in navs):
        fail(f"[{lang}] aria-label 없는 nav")
    for t, a in p.attrs_all:
        if t == "a" and a.get("data-lang") and not a.get("lang"):
            fail(f"[{lang}] 언어 링크에 lang 속성 없음: {a.get('href')}")
    check_sections(lang, path.read_text(encoding="utf-8"))
    check_mascot(lang, path.read_text(encoding="utf-8"))
    return p


SECTIONS = ["hero", "try", "features", "audience", "faq", "cta", "footer"]


def check_sections(lang, html):
    """요금 비교 구역은 두지 않는다 (설치 전환 목적 — 사용자 결정). 구독 안내는 FAQ 에서만."""
    import re
    ids = [i for i in re.findall(r'<(?:section|footer)[^>]*\bid="([\w-]+)"', html)]
    ids = [i for i in ids if i in SECTIONS or i == "plans"]
    if ids != SECTIONS:
        fail(f"[{lang}] 구역 순서/개수 불일치: {ids}")
    faq = re.search(r'id="faq".*?</section>', html, re.S)
    n = len(re.findall(r"<details", faq.group(0))) if faq else 0
    if not 5 <= n <= 7:
        fail(f"[{lang}] FAQ {n}개 (5~7개여야 함)")
    if faq and not re.search(r"(인피니트 노트|Infinite Note|无限音符)", faq.group(0)):
        fail(f"[{lang}] FAQ 에 구독 안내가 없음 (무료 표현만 남으면 오해)")


HTML_LANG = {"ko": "ko", "en": "en", "zh": "zh-Hans"}
HREFLANG = {"ko": SITE + AE_BASE, "en": SITE + AE_BASE + "en/",
            "zh-Hans": SITE + AE_BASE + "zh/", "x-default": SITE + AE_BASE}


def check_lang_meta(lang, p):
    html_tag = next((a for t, a in p.attrs_all if t == "html"), {})
    if html_tag.get("lang") != HTML_LANG[lang]:
        fail(f"[{lang}] <html lang> = {html_tag.get('lang')}")
    alts = {a.get("hreflang"): a.get("href") for t, a in p.attrs_all
            if t == "link" and a.get("rel") == "alternate"}
    if alts != HREFLANG:
        fail(f"[{lang}] hreflang 불일치: {alts}")
    if not any(t == "script" and a.get("src") == "/assets/js/lang.js" for t, a in p.attrs_all):
        fail(f"[{lang}] lang.js 없음")
    if html_tag.get("data-base") != AE_BASE:
        fail(f"[{lang}] <html data-base> = {html_tag.get('data-base')} (lang.js 가 묶음 주소를 읽는 곳)")


def check_meta(lang, p):
    metas = {(a.get("property") or a.get("name")): a.get("content") for t, a in p.attrs_all if t == "meta"}
    for k in ("description", "og:title", "og:description", "og:image", "og:url", "twitter:card", "apple-itunes-app"):
        if not metas.get(k):
            fail(f"[{lang}] meta {k} 없음")
    if metas.get("twitter:card") != "summary_large_image":
        fail(f"[{lang}] twitter:card 값 오류")
    if "app-id=6739764701" not in (metas.get("apple-itunes-app") or ""):
        fail(f"[{lang}] apple-itunes-app app-id 오류")
    img = (metas.get("og:image") or "").replace("https://tigerstone1263.com", "")
    if img and not (ROOT / img.lstrip("/")).exists():
        fail(f"[{lang}] og:image 파일 없음: {img}")
    links = {a.get("rel"): a.get("href") for t, a in p.attrs_all if t == "link"}
    if links.get("canonical") != HREFLANG[HTML_LANG[lang]]:
        fail(f"[{lang}] canonical 오류: {links.get('canonical')}")
    for rel in ("icon", "apple-touch-icon"):
        href = links.get(rel)
        if not href or not (ROOT / href.lstrip("/")).exists():
            fail(f"[{lang}] {rel} 없음")
    if not "".join(p.title_text).strip():
        fail(f"[{lang}] title 없음")


SHOTS = ["phone-hero", "feat-ear", "feat-staff", "feat-create", "game-map"]


def check_shot_resolution():
    """폰 화면은 최대 300 CSS px 로 보이므로 2~3배 화면에서 선명하려면 폭 720px 이상, 파일은 250KB 이하."""
    from PIL import Image
    for lang in PAGES:
        for n in SHOTS:
            f = AE_ASSETS / "img" / "shots" / lang / f"{n}.webp"
            if not f.exists():
                fail(f"shots/{lang}/{n}.webp 없음")
                continue
            w = Image.open(f).size[0]
            if w < 720:
                fail(f"shots/{lang}/{n}.webp 폭 {w}px (720 이상이어야 선명)")
            if f.stat().st_size > 250_000:
                fail(f"shots/{lang}/{n}.webp {f.stat().st_size // 1000}KB (250KB 이하)")
        # 언어 페이지는 자기 언어의 앱 화면만 쓴다
        html = (ROOT / PAGES[lang]).read_text(encoding="utf-8")
        for other in PAGES:
            if other != lang and f"{A}/img/shots/{other}/" in html:
                fail(f"[{lang}] 다른 언어({other}) 앱 화면을 쓴다")
        if f"{A}/img/shots/{lang}/" not in html:
            fail(f"[{lang}] 자기 언어 앱 화면이 없다")


APP_SORI = Path.home() / "abp" / "absolute_ear" / "assets" / "images" / "mascot" / "sori.webp"


def check_lang_banner(lang, p):
    """루트(한국어) 페이지에만 숨겨진 안내 띠가 있고, 띠의 링크는 고른 언어를 기억하는 data-lang 링크여야 한다."""
    banner = [a for t, a in p.attrs_all if t == "div" and a.get("id") == "lang-banner"]
    if lang != "ko":
        if banner:
            fail(f"[{lang}] 안내 띠는 루트 페이지에만 있어야 함")
        return
    if len(banner) != 1 or "hidden" not in banner[0]:
        fail("[ko] 숨겨진 #lang-banner 없음")
    for target in ("en", "zh"):
        if not any(t == "a" and a.get("data-lang") == target and a.get("href") == f"{AE_BASE}{target}/" and a.get("class") == "lang-banner-link"
                   for t, a in p.attrs_all):
            fail(f"[ko] 안내 띠에 {target} 링크 없음")


CHIP_CLASSES = ["c-interval", "c-scale", "c-chord", "c-melody", "c-prog", "c-rhythm"]


def check_design(lang, p, html):
    """디자인 골격: 상단 내비, 카테고리 색 칩, 등장 애니메이션 스크립트, 구역 머리말."""
    import re
    if not any(t == "nav" and "topnav" in (a.get("class") or "") and a.get("aria-label") for t, a in p.attrs_all):
        fail(f"[{lang}] aria-label 있는 상단 내비(.topnav) 없음")
    if not any(t == "a" and a.get("href") == "#cta" and "nav-cta" in (a.get("class") or "") for t, a in p.attrs_all):
        fail(f"[{lang}] 내비 다운로드 버튼(#cta) 없음")
    # 소리 소개 구역은 뺐다(2026-10-31 사용자 결정) — 동작 영상·#sori 링크가 남으면 안 된다
    if any(t == "video" for t, a in p.attrs_all) or any(t == "a" and a.get("href") == "#sori" for t, a in p.attrs_all):
        fail(f"[{lang}] 소리 소개 구역의 영상이나 #sori 링크가 남아 있음")
    # 청음 맛보기: 앱과 같은 세 음정 보기, 결과 안내는 스크린리더에 읽힘
    ivs = [a.get("data-iv") for t, a in p.attrs_all if t == "button" and a.get("data-iv")]
    if ivs != ["maj3", "p4", "p5"]:
        fail(f"[{lang}] 청음 맛보기 보기 버튼 불일치: {ivs}")
    if not any(a.get("aria-live") == "polite" and "try-feedback" in (a.get("class") or "") for t, a in p.attrs_all):
        fail(f"[{lang}] 청음 맛보기 결과에 aria-live 없음")
    sec_try = re.search(r'<section id="try".*?</section>', html, re.S)
    if sec_try:
        bare = re.sub(r'<span[^>]*aria-hidden="true"[^>]*>.*?</span>', '', sec_try.group(0), flags=re.S)
        for g in ("▶", "↻", "→"):
            if g in bare:
                fail(f"[{lang}] 청음 맛보기에 스크린리더가 읽는 기호 {g} (aria-hidden 으로 감싸야 함)")
        if 'class="try-fallback"' not in sec_try.group(0):
            fail(f"[{lang}] 체험을 못 할 때의 안내(try-fallback) 없음")
        if 'role="status"' not in sec_try.group(0):
            fail(f"[{lang}] 결과 문장에 role=status 없음")
    if not any(t == "script" and a.get("src") == f"{A}/js/eartest.js" and "defer" in a for t, a in p.attrs_all):
        fail(f"[{lang}] eartest.js(defer) 없음")
    # 데스크톱 QR → /AbsoluteEar/get/ (기기에 맞는 스토어로 이동)
    if not any(t == "img" and a.get("src") == f"{A}/img/qr-get.svg" for t, a in p.attrs_all):
        fail(f"[{lang}] 설치 QR 없음")
    if not any(t == "script" and a.get("src") == "/assets/js/reveal.js" and "defer" in a for t, a in p.attrs_all):
        fail(f"[{lang}] reveal.js(defer) 없음")
    # 첫 화면 폰 두 장은 표시 크기(≤270px)에 맞는 작은 이미지를 srcset 으로, 앞 폰은 우선 로드
    for t, a in p.attrs_all:
        if t == "img" and "phone" in (a.get("class") or "").split():
            if "480w" not in (a.get("srcset") or "") or not a.get("sizes"):
                fail(f"[{lang}] 히어로 폰 이미지에 srcset/sizes 없음: {a.get('src')}")
            if "phone-front" in a.get("class") and a.get("fetchpriority") != "high":
                fail(f"[{lang}] 앞 폰(LCP)에 fetchpriority=high 없음")
    for zone in ("hero", "cta"):
        m = re.search(rf'<section id="{zone}".*?</section>', html, re.S)
        n = len(re.findall(r'<a class="store-btn', m.group(0))) if m else 0
        if n != 2:
            fail(f"[{lang}] {zone} 구역 스토어 버튼 {n}개 (2개여야 함)")
    if re.search(r"radial-gradient|linear-gradient|backdrop-filter", CSS.read_text(encoding="utf-8")):
        fail(f"[{lang}] 그라데이션·블러 장식 사용 (흑백·평면 톤 유지)")
    cards = re.findall(r'<article class="fcard', html)
    if len(cards) != 4:
        fail(f"[{lang}] 기능 카드 {len(cards)}개 (4개여야 함)")
    # MotionSites 업그레이드 뼈대: 시그니처 워드마크, 굴러가는 알약 버튼, 쌓이는 기능 카드, 등장 모션, 질감
    hero = re.search(r'<section id="hero".*?</section>', html, re.S)
    hero_html = hero.group(0) if hero else ""
    # 워드마크는 장식 — 실제 글자로 두면 접근성 대비 검사에 걸리므로 CSS 의사 요소(data-text)로 그린다
    if not re.search(r'<div class="hero-wordmark" aria-hidden="true" data-text="Absolute Ear"></div>', hero_html):
        fail(f"[{lang}] 첫 화면 시그니처 워드마크 없음(장식은 data-text 의사 요소로)")
    css = CSS.read_text(encoding="utf-8")
    m = re.search(r"@keyframes riseIn \{([^}]*\})", css)
    if not m or "opacity" in m.group(1):
        fail("첫 화면 폰(LCP) 등장 애니메이션이 투명도를 바꿈 — LCP 가 늦어진다")
    if len(re.findall(r'class="in-blur[ "]', hero_html)) < 2:
        fail(f"[{lang}] 제목 줄별 blur-rise 등장 없음")
    for zone in ("hero", "cta"):
        m = re.search(rf'<section id="{zone}".*?</section>', html, re.S)
        btns = re.findall(r'<a class="store-btn[^"]*".*?</a>', m.group(0) if m else "", re.S)
        if not btns or not all("btn-roll__chip" in b and "btn-roll__inner" in b for b in btns):
            fail(f"[{lang}] {zone} 스토어 버튼이 굴러가는 알약 버튼이 아님")
    slots = re.findall(r'<div class="stack-slot" style="--i:\d">\s*<article class="fcard', html)
    if len(slots) != 4:
        fail(f"[{lang}] 쌓이는 기능 카드 슬롯 {len(slots)}개 (4개여야 함)")
    # 스크롤 연출: 무대(hero-stage)와 자막, cine.js(defer). 긴 활주로 높이는 JS 가 cine-on 을 달 때만 (JS 없으면 정적 첫 화면)
    if '<div class="hero-stage">' not in hero_html or 'class="hero-caption"' not in hero_html:
        fail(f"[{lang}] 첫 화면 연출 무대·자막 없음")
    if not any(t == "script" and a.get("src") == f"{A}/js/cine.js" and "defer" in a for t, a in p.attrs_all):
        fail(f"[{lang}] cine.js(defer) 없음")
    css_all = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css_all):
        if "--runway" in body and "height" in body and ".cine-on" not in sel:
            fail(f"연출 활주로 높이가 cine-on 없이 걸림: {sel.strip()}")
    if '<div class="page-grain" aria-hidden="true"></div>' not in html:
        fail(f"[{lang}] 종이 질감 레이어 없음")
    for sec in ("try", "audience", "features", "faq"):
        m = re.search(rf'<section id="{sec}".*?</h2>', html, re.S)
        if not m or 'class="eyebrow"' not in m.group(0):
            fail(f"[{lang}] {sec} 구역 제목 위에 eyebrow 없음")


def check_try_frames():
    """청음 맛보기의 소리 프레임 4장은 모두 같은 배경(음정 카테고리 #b6c6d8)이어야 한다 — 상태마다 색이 바뀌면 안 됨."""
    from PIL import Image
    for name in ("idle", "listen", "yes", "no"):
        im = Image.open(AE_ASSETS / "img" / "poses" / f"try-{name}.webp").convert("RGB")
        w, h = im.size
        for x, y in ((3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4)):
            px = im.getpixel((x, y))
            if max(abs(a - b) for a, b in zip(px, (0xB6, 0xC6, 0xD8))) > 6:
                fail(f"try-{name}.webp 배경이 음정 카테고리 색이 아님: {px}")
                break


def check_zh_store_order():
    """중국어 페이지는 기기와 상관없이 App Store 먼저 — 기기별 강조 규칙은 zh 를 빼고 걸어야 한다."""
    css = CSS.read_text(encoding="utf-8")
    for sel in re.findall(r"([^{}]*\.os-(?:android|ios)[^{}]*)\{", css):
        for part in sel.split(","):
            if ".os-" in part and ':not([lang^="zh"])' not in part:
                fail(f"기기별 스토어 강조가 중국어 페이지에도 걸림: {part.strip()}")


def check_reveal_needs_js():
    """등장 애니메이션은 <html class="js"> 일 때만 숨긴다 — JS 가 없으면 내용이 처음부터 보여야 한다."""
    import re
    css = CSS.read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if ".reveal" in sel and "opacity: 0" in body and not all(part.strip().startswith(".js ") for part in sel.split(",")):
            fail(f"JS 없이도 숨겨지는 reveal 규칙: {sel.strip()}")


def check_mascot(lang, html):
    """마스코트 그림은 앱 원본 소리여야 한다 (생성 그림은 생김새가 달라 사용자 반려)."""
    import re
    srcs = re.findall(r'<img class="(?:hero|cta)-sori" src="([^"]+)"', html)
    if len(srcs) != 2 or any(s != f"{A}/img/sori.webp" for s in srcs):
        fail(f"[{lang}] 히어로·CTA 마스코트가 sori.webp 가 아님: {srcs}")


def check_mascot_matches_app():
    from PIL import Image, ImageChops, ImageStat
    if not APP_SORI.exists():
        return
    site = Image.open(AE_ASSETS / "img" / "sori.webp").convert("RGBA")
    app = Image.open(APP_SORI).convert("RGBA")
    app = app.crop(app.getbbox())
    a, b = site.resize((64, 64)), app.resize((64, 64))
    diff = sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 4
    if diff > 6:
        fail(f"sori.webp 가 앱 원본과 다름 (평균 차이 {diff:.1f})")


def check_sitemap():
    f = ROOT / "sitemap.xml"
    if not f.exists():
        fail("sitemap.xml 없음")
        return
    xml = f.read_text(encoding="utf-8")
    want = [SITE + build.lang_path(g["base"], l) for g in build.GROUPS for l in build.LANGS]
    if sorted(re.findall(r"<loc>([^<]+)</loc>", xml)) != sorted(want):
        fail(f"sitemap 주소 불일치: {re.findall(r'<loc>([^<]+)</loc>', xml)}")
    for url in want:
        if f"<loc>{url}</loc>" not in xml:
            fail(f"sitemap 에 {url} 없음")
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        alts = dict(re.findall(r'hreflang="([^"]+)" href="([^"]+)"', block))
        if set(alts) != {"ko", "en", "zh-Hans", "x-default"}:
            fail(f"sitemap hreflang 불완전: {sorted(alts)}")
    if not (ROOT / "robots.txt").exists():
        fail("robots.txt 없음")


STUDIO_FORBIDDEN = ["작곡", "compos", "作曲", "创作", "나리", "₩", "$"]
SORI_CLIPS = ["idle", "listen", "celebrate", "wave"]


def check_studio(lang, rel):
    """루트(tigerstone) 페이지: 주소 메타, AE 로 가는 길, 스토어 버튼, 금지 표현, 연출 뼈대."""
    path = ROOT / rel
    if not path.exists():
        fail(f"[root/{lang}] {rel} 없음")
        return
    html = path.read_text(encoding="utf-8")
    p = parse(path)
    tag = f"[root/{lang}]"
    html_tag = next((a for t, a in p.attrs_all if t == "html"), {})
    if html_tag.get("lang") != HTML_LANG[lang] or html_tag.get("data-base") != "/":
        fail(f"{tag} <html lang/data-base> = {html_tag}")
    want = {"ko": SITE + "/", "en": SITE + "/en/", "zh-Hans": SITE + "/zh/", "x-default": SITE + "/"}
    alts = {a.get("hreflang"): a.get("href") for t, a in p.attrs_all if t == "link" and a.get("rel") == "alternate"}
    if alts != want:
        fail(f"{tag} hreflang 불일치: {alts}")
    links = {a.get("rel"): a.get("href") for t, a in p.attrs_all if t == "link"}
    if links.get("canonical") != want[HTML_LANG[lang]]:
        fail(f"{tag} canonical 오류: {links.get('canonical')}")
    metas = {(a.get("property") or a.get("name")): a.get("content") for t, a in p.attrs_all if t == "meta"}
    for k in ("description", "og:title", "og:description", "og:image", "og:url"):
        if not metas.get(k):
            fail(f"{tag} meta {k} 없음")
    img = (metas.get("og:image") or "").replace(SITE, "")
    if not img.startswith("/assets/") or not (ROOT / img.lstrip("/")).exists():
        fail(f"{tag} og:image 가 루트 전용 이미지가 아님: {img}")
    if not "".join(p.title_text).strip():
        fail(f"{tag} title 없음")
    # 앱으로 가는 길: 같은 언어의 AE 페이지, 스토어 버튼 2개(utm studio)
    if build.lang_path(AE_BASE, lang) not in p.links:
        fail(f"{tag} 같은 언어 AE 페이지 링크 없음")
    m = re.search(r'<section id="apps".*?</section>', html, re.S)
    btns = re.findall(r'<a class="store-btn[^"]*".*?</a>', m.group(0) if m else "", re.S)
    if len(btns) != 2 or not all("btn-roll__chip" in b for b in btns):
        fail(f"{tag} 앱 카드 스토어 버튼 {len(btns)}개 (굴러가는 알약 2개여야 함)")
    if not any(PLAY in h and "utm_campaign%3Dstudio" in h for h in p.links) or not any(APP_STORE in h for h in p.links):
        fail(f"{tag} 스토어 링크(Play utm studio·App Store) 없음")
    if "mailto:tigerstone1263@gmail.com" not in p.links:
        fail(f"{tag} 문의 메일 링크 없음")
    text = "".join(p.text)
    for w in STUDIO_FORBIDDEN:
        if w in text:
            fail(f"{tag} 금지 표현: {w}")
    if "Google LLC" not in text or "Apple Inc." not in text:
        fail(f"{tag} 스토어 상표 고지 없음")
    for src in p.scripts:
        if src and src.startswith(("http:", "https:", "//")):
            fail(f"{tag} 외부 스크립트: {src}")
    if any(not a.get("aria-label") for t, a in p.attrs_all if t == "nav"):
        fail(f"{tag} aria-label 없는 nav")
    for t, a in p.attrs_all:
        if t == "a" and a.get("data-lang") and not a.get("lang"):
            fail(f"{tag} 언어 링크에 lang 속성 없음: {a.get('href')}")
    # 연출 뼈대: 무대, 갈라지는 두 덩이 글자(장식이라 aria-hidden, h1 에 aria-label), 장면 3개, 소리 자리 2곳
    if '<section id="stage" class="stage" data-scene="0">' not in html:
        fail(f"{tag} 스크롤 무대 없음")
    if not re.search(r'<h1 class="mark" aria-label="tigerstone">', html) or html.count('class="mark-half') != 2:
        fail(f"{tag} tigerstone 글자 무대(두 덩이) 없음")
    if len(re.findall(r'<li class="scene scene-\d">', html)) != 3:
        fail(f"{tag} 장면 3개가 아님")
    for spot in ("stage", "card"):
        if f'data-sori="{spot}"' not in html:
            fail(f"{tag} 소리 자리({spot}) 없음")
    if html.count('class="sori-still"') != 2:
        fail(f"{tag} 소리 정지 그림(동작 줄이기·재생 실패 대비) 없음")
    if '<script src="/assets/js/studio.js" defer></script>' not in html:
        fail(f"{tag} studio.js(defer) 없음")
    for other in STUDIO_PAGES:
        if other != lang and f"/shots/{other}/" in html:
            fail(f"{tag} 다른 언어({other}) 앱 화면을 쓴다")
    banner = [a for t, a in p.attrs_all if t == "div" and a.get("id") == "lang-banner"]
    if (lang == "ko") != bool(banner):
        fail(f"{tag} 언어 안내 띠는 한국어 루트에만")
    if lang == "ko":
        for target in ("en", "zh"):
            if not any(t == "a" and a.get("data-lang") == target and a.get("href") == f"/{target}/" for t, a in p.attrs_all):
                fail(f"{tag} 안내 띠에 {target} 링크 없음")


def check_studio_assets():
    css = re.sub(r"/\*.*?\*/", "", STUDIO_CSS.read_text(encoding="utf-8"), flags=re.S)
    if re.search(r"radial-gradient|linear-gradient|conic-gradient|backdrop-filter|text-shadow", css):
        fail("studio.css: 그라데이션·블러 배경·글로우 사용 (흑백·평면 톤 유지)")
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if ".reveal" in sel and "opacity: 0" in body and not all(part.strip().startswith(".js ") for part in sel.split(",")):
            fail(f"studio.css: JS 없이도 숨겨지는 reveal 규칙: {sel.strip()}")
        if "height" in body and "svh" in body and ".stage" in sel and ".cine-on" not in sel:
            fail(f"studio.css: 활주로 높이가 cine-on 없이 걸림: {sel.strip()}")
        # 등장 애니메이션(fill both)이 스크롤로 바꾸는 투명도를 덮어쓰지 않게: 같은 규칙에 둘 다 두지 않는다
        if "animation:" in body and "var(--split" in body:
            fail(f"studio.css: 스크롤 투명도와 등장 애니메이션이 같은 요소에: {sel.strip()}")
    for sel in re.findall(r"([^{}]*\.os-(?:android|ios)[^{}]*)\{", css):
        for part in sel.split(","):
            if ".os-" in part and ':not([lang^="zh"])' not in part:
                fail(f"studio.css: 기기별 스토어 강조가 중국어 페이지에도 걸림: {part.strip()}")
    for name in SORI_CLIPS:
        for ext in ("webm", "mov"):
            f = ROOT / "assets" / "media" / f"sori-{name}.{ext}"
            if not f.exists():
                fail(f"소리 영상 없음: {f.relative_to(ROOT)}")
            elif f.stat().st_size > 260_000:
                fail(f"소리 영상 {f.name} {f.stat().st_size // 1000}KB (260KB 이하)")


def check_policy_copies():
    """앱 폴더의 정책 주소는 루트 정책 파일의 사본이다. 지정한 치환 말고는 한 글자도 달라선 안 된다."""
    for dst, (src, subs) in build.POLICY_COPIES.items():
        f = ROOT / dst
        if not f.exists():
            fail(f"정책 사본 없음: {dst}")
            continue
        want = build.policy_copy((ROOT / src).read_text(encoding="utf-8"), subs)
        if f.read_text(encoding="utf-8") != want:
            fail(f"정책 사본이 원본({src})+지정 치환과 다름: {dst}")
    if (ROOT / "AbsoluteEar" / "PrivacyPolicy.html").read_bytes() != (ROOT / "AbsoluteEarPolicy.html").read_bytes():
        fail("AbsoluteEar/PrivacyPolicy.html 이 AbsoluteEarPolicy.html 과 바이트가 다름")
    if "Real Absolute Pitch" in (ROOT / "AbsoluteEar" / "TermsOfService.html").read_text(encoding="utf-8"):
        fail("AbsoluteEar/TermsOfService.html 에 다른 앱 이름이 남음")


def resolve(url_path):
    """GitHub Pages 가 그 주소에 내주는 파일. 끝이 / 면 index.html, 확장자가 없으면 .html 을 붙인다."""
    rel = url_path.split("#")[0].split("?")[0].lstrip("/")
    if rel == "" or rel.endswith("/"):
        return ROOT / rel / "index.html"
    f = ROOT / rel
    if "." not in rel.rsplit("/", 1)[-1]:
        return f.with_name(f.name + ".html")
    return f


def check_internal_refs():
    """만든 페이지 안의 모든 내부 주소(href·src·srcset·data-frame-*)가 실제 파일로 열려야 한다. 404 구제 목록도 같다."""
    files = list(STUDIO_PAGES.values()) + list(PAGES.values()) + ["get/index.html", "AbsoluteEar/get/index.html", "404.html"]
    for rel in files:
        html = (ROOT / rel).read_text(encoding="utf-8")
        refs = re.findall(r'(?:href|src|data-frame-[a-z]+)="(/[^"/][^"]*|/)"', html)
        for srcset in re.findall(r'srcset="([^"]+)"', html):
            refs += [part.strip().split(" ")[0] for part in srcset.split(",")]
        for ref in refs:
            if ref.startswith("//"):
                continue
            if not resolve(ref).exists():
                fail(f"[{rel}] 열리지 않는 내부 주소: {ref}")
    known = build.known_paths(build.GROUPS)
    m = re.search(r"var KNOWN = (\[.*?\]);", (ROOT / "404.html").read_text(encoding="utf-8"))
    if not m or json.loads(m.group(1)) != known:
        fail("404.html 의 구제 목록이 build.known_paths 와 다름")
    for k in known:
        if not resolve(k).exists():
            fail(f"404 구제 목록의 주소가 열리지 않음: {k}")


def check_zh_spacing():
    d = {**json.loads((DEV / "strings" / "zh.json").read_text(encoding="utf-8")),
         **{"studio." + k: v for k, v in json.loads((DEV / "studio" / "strings" / "zh.json").read_text(encoding="utf-8")).items()}}
    for k, v in d.items():
        if re.search(r"[\u4e00-\u9fff，、。](</span>)? (<span[^>]*>)?[\u4e00-\u9fff]", v):
            fail(f"[zh] {k}: 한자 사이에 공백")


def check_string_keys():
    for folder in (DEV / "strings", DEV / "studio" / "strings"):
        check_string_keys_in(folder)


def check_string_keys_in(folder):
    keys = {}
    for lang in PAGES:
        f = folder / f"{lang}.json"
        if f.exists():
            keys[lang] = set(json.loads(f.read_text(encoding="utf-8")))
        else:
            fail(f"문구 파일 없음: {lang}.json")
    base = keys.get("ko", set())
    for lang, k in keys.items():
        if k != base:
            fail(f"[{lang}] 키 불일치: 빠짐 {sorted(base - k)} / 남음 {sorted(k - base)}")


def temp_site(tmp):
    """빌드에 필요한 것만 임시 폴더로 복사하고, 고치지 않은 상태로는 빌드가 성공하는지 먼저 확인한다
    (필요한 파일이 빠져 엉뚱한 이유로 실패하면 '실패해야 하는' 검사가 거짓 통과한다)."""
    import shutil
    import subprocess
    shutil.copytree(DEV, tmp / "_dev")
    shutil.copytree(ROOT / "assets", tmp / "assets")
    shutil.copytree(ROOT / "AbsoluteEar", tmp / "AbsoluteEar")
    for name in json.loads((DEV / "policy_hashes.json").read_text()):
        shutil.copy(ROOT / name, tmp / name)
    r = subprocess.run([sys.executable, str(tmp / "_dev" / "build.py")], capture_output=True, text=True)
    if r.returncode != 0:
        fail("임시 폴더 빌드가 그대로도 실패함: " + (r.stderr.strip().splitlines() or ["?"])[-1])
        return False
    for f in [tmp / rel for rel in PAGES.values()]:
        f.unlink()
    return True


def check_build_rejects_missing_key():
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if not temp_site(tmp):
            return
        f = tmp / "_dev" / "strings" / "en.json"
        if not f.exists():
            fail("빌드 키 누락 검사: en.json 없음")
            return
        d = json.loads(f.read_text(encoding="utf-8"))
        d.pop("hero_title")
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, str(tmp / "_dev" / "build.py")], capture_output=True)
        if r.returncode == 0:
            fail("문구 키가 빠져도 빌드가 성공함")


def check_get_page():
    f = ROOT / "AbsoluteEar" / "get" / "index.html"
    if not f.exists():
        fail("AbsoluteEar/get/index.html 없음")
        return
    old = ROOT / "get" / "index.html"
    if not old.exists() or old.read_bytes() != f.read_bytes():
        fail("옛 QR 주소 get/index.html 이 AbsoluteEar/get/index.html 과 다름 (build.py 가 복사)")
    html = f.read_text(encoding="utf-8")
    for need in ("apps.apple.com/app/id6739764701", "id=com.tigerstone.AbsoluteEar", 'name="robots" content="noindex"'):
        if need not in html:
            fail(f"get/index.html 에 {need} 없음")
    if re.search(r'<script[^>]+src=', html):
        fail("get/index.html 에 외부 스크립트")
    qr = AE_ASSETS / "img" / "qr-get.svg"
    if not qr.exists() or "<svg" not in qr.read_text(encoding="utf-8"):
        fail("AbsoluteEar/assets/img/qr-get.svg 없음")


def check_node_tests():
    import subprocess
    for t in ("test_eartest.js", "test_eartest_dom.js", "test_os.js", "test_cine.js", "test_404.js", "test_studio.js"):
        r = subprocess.run(["node", str(DEV / t)], capture_output=True, text=True)
        if r.returncode != 0:
            fail((r.stdout.strip() or r.stderr.strip().splitlines()[-1]) + f" ({t})")


def check_lang_js():
    import subprocess
    r = subprocess.run(["node", str(DEV / "test_lang.js")], capture_output=True, text=True)
    if r.returncode != 0:
        fail(r.stdout.strip() or r.stderr.strip())


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LAYOUTS = [(360, 1), (360, 1.15), (320, 1), (320, 1.15), (390, 1.15), (768, 1), (1024, 1), (1280, 1), (1440, 1)]


def check_layout():
    """실제 Chrome 으로 언어 × 폭마다 글자 넘침·가로 스크롤·배지 튀어나옴을 측정한다."""
    import html as htmllib
    import re
    import socket
    import subprocess
    import tempfile
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "-b", "127.0.0.1"],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import time; time.sleep(0.8)
        targets = [(f"{lang}", build.lang_path(AE_BASE, lang)) for lang in PAGES] + \
                  [(f"root/{lang}", build.lang_path("/", lang)) for lang in STUDIO_PAGES]
        for lang, path in targets:
            for w, scale in LAYOUTS:
                url = f"http://127.0.0.1:{port}/_dev/layout_check.html?w={w}&p={path}&scale={scale}"
                out = ""
                for _ in range(2):  # 헤드리스 Chrome 이 가끔 멈추면 한 번 더
                    with tempfile.TemporaryDirectory() as prof:
                        try:
                            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}",
                                                  "--lang=ko-KR", "--virtual-time-budget=8000", "--dump-dom", url],
                                                 capture_output=True, text=True, timeout=60).stdout
                        except subprocess.TimeoutExpired:
                            out = ""
                    if '<pre id="result">' in out and "pending" not in out:
                        break
                m = re.search(r'<pre id="result">(.*?)</pre>', out, re.S)
                res = htmllib.unescape(m.group(1)) if m else "결과 없음"
                if res == "pending" or res == "결과 없음":
                    fail(f"[{lang} {w}px x{scale}] 레이아웃 측정 실패")
                    continue
                for item in json.loads(res):
                    fail(f"[{lang} {w}px x{scale}] {item}")
    finally:
        server.terminate()


def check_build_requires_all_langs():
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if not temp_site(tmp):
            return
        (tmp / "_dev" / "strings" / "zh.json").unlink()
        r = subprocess.run([sys.executable, str(tmp / "_dev" / "build.py")], capture_output=True)
        if r.returncode == 0:
            fail("언어 JSON 이 없어도 빌드가 성공함")
        if any((tmp / rel).exists() for rel in PAGES.values()):
            fail("빌드가 실패했는데 일부 언어 html 을 써 버림")


def main():
    check_policy_files()
    check_policy_copies()
    check_internal_refs()
    check_build_requires_all_langs()
    check_lang_js()
    check_node_tests()
    check_get_page()
    check_string_keys()
    check_zh_spacing()
    check_build_rejects_missing_key()
    for lang, rel in STUDIO_PAGES.items():
        check_studio(lang, rel)
    check_studio_assets()
    for lang, rel in PAGES.items():
        p = check_page(lang, rel)
        if p:
            check_lang_meta(lang, p)
            check_meta(lang, p)
            check_lang_banner(lang, p)
            check_design(lang, p, (ROOT / rel).read_text(encoding="utf-8"))
    check_sitemap()
    check_shot_resolution()
    check_mascot_matches_app()
    check_reveal_needs_js()
    check_zh_store_order()
    check_try_frames()
    if "--no-layout" not in sys.argv:
        check_layout()
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
