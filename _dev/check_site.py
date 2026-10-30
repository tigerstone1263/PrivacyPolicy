"""홈페이지 정적 검사. 통과하면 OK, 실패하면 이유를 출력하고 exit 1."""
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEV = ROOT / "_dev"
PAGES = {"ko": "index.html", "en": "en/index.html", "zh": "zh/index.html"}

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
    for need in ("/AbsoluteEarPolicy.html", "/termsOfService.html", "mailto:tigerstone1263@gmail.com"):
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


SECTIONS = ["hero", "try", "features", "sori", "audience", "faq", "cta", "footer"]


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
HREFLANG = {"ko": "https://tigerstone1263.com/", "en": "https://tigerstone1263.com/en/",
            "zh-Hans": "https://tigerstone1263.com/zh/", "x-default": "https://tigerstone1263.com/"}


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
    for n in SHOTS:
        f = ROOT / "assets" / "img" / f"{n}.webp"
        w = Image.open(f).size[0]
        if w < 720:
            fail(f"{n}.webp 폭 {w}px (720 이상이어야 선명)")
        if f.stat().st_size > 250_000:
            fail(f"{n}.webp {f.stat().st_size // 1000}KB (250KB 이하)")


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
        if not any(t == "a" and a.get("data-lang") == target and a.get("href") == f"/{target}/" and a.get("class") == "lang-banner-link"
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
    # 소리 소개: 앱의 실제 카테고리별 동작 6개 — 정지 프레임(poster) + 반복 영상(mp4)
    vids = [a for t, a in p.attrs_all if t == "video" and "pose-video" in (a.get("class") or "")]
    want = [f"/assets/img/poses/sori-{c[2:]}.webp" for c in CHIP_CLASSES]
    if [a.get("poster") for a in vids] != want:
        fail(f"[{lang}] 소리 동작 영상 순서 불일치: {[a.get('poster') for a in vids]}")
    for a in vids:
        for key in ("muted", "loop", "playsinline"):
            if key not in a:
                fail(f"[{lang}] 동작 영상에 {key} 없음: {a.get('poster')}")
        if a.get("preload") != "none":
            fail(f"[{lang}] 동작 영상은 preload=none 이어야 함")
        mp4 = ROOT / a.get("poster", "").lstrip("/").replace(".webp", ".mp4")
        if not mp4.exists() or mp4.stat().st_size > 250_000:
            fail(f"[{lang}] 동작 영상 없음 또는 250KB 초과: {mp4.name}")
    # 청음 맛보기: 앱과 같은 세 음정 보기, 결과 안내는 스크린리더에 읽힘
    ivs = [a.get("data-iv") for t, a in p.attrs_all if t == "button" and a.get("data-iv")]
    if ivs != ["m3", "p4", "p5"]:
        fail(f"[{lang}] 청음 맛보기 보기 버튼 불일치: {ivs}")
    if not any(a.get("aria-live") == "polite" and "try-feedback" in (a.get("class") or "") for t, a in p.attrs_all):
        fail(f"[{lang}] 청음 맛보기 결과에 aria-live 없음")
    if not any(t == "script" and a.get("src") == "/assets/js/eartest.js" and "defer" in a for t, a in p.attrs_all):
        fail(f"[{lang}] eartest.js(defer) 없음")
    # 데스크톱 QR → /get/ (기기에 맞는 스토어로 이동)
    if not any(t == "img" and a.get("src") == "/assets/img/qr-get.svg" for t, a in p.attrs_all):
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
    if re.search(r"radial-gradient|linear-gradient|backdrop-filter", (ROOT / "assets" / "css" / "site.css").read_text(encoding="utf-8")):
        fail(f"[{lang}] 그라데이션·블러 장식 사용 (흑백·평면 톤 유지)")
    cards = re.findall(r'<article class="fcard', html)
    if len(cards) != 4:
        fail(f"[{lang}] 기능 카드 {len(cards)}개 (4개여야 함)")
    for sec in ("try", "audience", "features", "sori", "faq"):
        m = re.search(rf'<section id="{sec}".*?</h2>', html, re.S)
        if not m or 'class="eyebrow"' not in m.group(0):
            fail(f"[{lang}] {sec} 구역 제목 위에 eyebrow 없음")


def check_reveal_needs_js():
    """등장 애니메이션은 <html class="js"> 일 때만 숨긴다 — JS 가 없으면 내용이 처음부터 보여야 한다."""
    import re
    css = (ROOT / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if ".reveal" in sel and "opacity: 0" in body and not all(part.strip().startswith(".js ") for part in sel.split(",")):
            fail(f"JS 없이도 숨겨지는 reveal 규칙: {sel.strip()}")


def check_mascot(lang, html):
    """마스코트 그림은 앱 원본 소리여야 한다 (생성 그림은 생김새가 달라 사용자 반려)."""
    import re
    srcs = re.findall(r'<img class="(?:hero|cta)-sori" src="([^"]+)"', html)
    if len(srcs) != 2 or any(s != "/assets/img/sori.webp" for s in srcs):
        fail(f"[{lang}] 히어로·CTA 마스코트가 sori.webp 가 아님: {srcs}")


def check_mascot_matches_app():
    from PIL import Image, ImageChops, ImageStat
    if not APP_SORI.exists():
        return
    site = Image.open(ROOT / "assets" / "img" / "sori.webp").convert("RGBA")
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
    for url in ("https://tigerstone1263.com/", "https://tigerstone1263.com/en/", "https://tigerstone1263.com/zh/"):
        if f"<loc>{url}</loc>" not in xml:
            fail(f"sitemap 에 {url} 없음")
    import re
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        alts = dict(re.findall(r'hreflang="([^"]+)" href="([^"]+)"', block))
        if set(alts) != {"ko", "en", "zh-Hans", "x-default"}:
            fail(f"sitemap hreflang 불완전: {sorted(alts)}")
    if not (ROOT / "robots.txt").exists():
        fail("robots.txt 없음")


def check_zh_spacing():
    import re
    d = json.loads((DEV / "strings" / "zh.json").read_text(encoding="utf-8"))
    for k, v in d.items():
        if re.search(r"[\u4e00-\u9fff，、。](</span>)? (<span[^>]*>)?[\u4e00-\u9fff]", v):
            fail(f"[zh] {k}: 한자 사이에 공백")


def check_string_keys():
    keys = {}
    for lang in PAGES:
        f = DEV / "strings" / f"{lang}.json"
        if f.exists():
            keys[lang] = set(json.loads(f.read_text(encoding="utf-8")))
        else:
            fail(f"문구 파일 없음: {lang}.json")
    base = keys.get("ko", set())
    for lang, k in keys.items():
        if k != base:
            fail(f"[{lang}] 키 불일치: 빠짐 {sorted(base - k)} / 남음 {sorted(k - base)}")


def check_build_rejects_missing_key():
    import shutil
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copytree(DEV, tmp / "_dev")
        shutil.copytree(ROOT / "assets", tmp / "assets")
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
    f = ROOT / "get" / "index.html"
    if not f.exists():
        fail("get/index.html 없음")
        return
    html = f.read_text(encoding="utf-8")
    for need in ("apps.apple.com/app/id6739764701", "id=com.tigerstone.AbsoluteEar", 'name="robots" content="noindex"'):
        if need not in html:
            fail(f"get/index.html 에 {need} 없음")
    if re.search(r'<script[^>]+src=', html):
        fail("get/index.html 에 외부 스크립트")
    qr = ROOT / "assets" / "img" / "qr-get.svg"
    if not qr.exists() or "<svg" not in qr.read_text(encoding="utf-8"):
        fail("assets/img/qr-get.svg 없음")


def check_node_tests():
    import subprocess
    for t in ("test_eartest.js", "test_os.js"):
        r = subprocess.run(["node", str(DEV / t)], capture_output=True, text=True)
        if r.returncode != 0:
            fail((r.stdout.strip() or r.stderr.strip().splitlines()[-1]) + f" ({t})")


def check_lang_js():
    import subprocess
    r = subprocess.run(["node", str(DEV / "test_lang.js")], capture_output=True, text=True)
    if r.returncode != 0:
        fail(r.stdout.strip() or r.stderr.strip())


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LAYOUTS = [(360, 1), (360, 1.15), (320, 1), (768, 1), (1024, 1), (1280, 1)]


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
        for lang in PAGES:
            path = "/" if lang == "ko" else f"/{lang}/"
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
    import shutil
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copytree(DEV, tmp / "_dev")
        shutil.copytree(ROOT / "assets", tmp / "assets")
        (tmp / "_dev" / "strings" / "zh.json").unlink()
        r = subprocess.run([sys.executable, str(tmp / "_dev" / "build.py")], capture_output=True)
        if r.returncode == 0:
            fail("언어 JSON 이 없어도 빌드가 성공함")
        if (tmp / "index.html").exists():
            fail("빌드가 실패했는데 일부 언어 html 을 써 버림")


def main():
    check_policy_files()
    check_build_requires_all_langs()
    check_lang_js()
    check_node_tests()
    check_get_page()
    check_string_keys()
    check_zh_spacing()
    check_build_rejects_missing_key()
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
    if "--no-layout" not in sys.argv:
        check_layout()
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
