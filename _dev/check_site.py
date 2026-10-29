"""홈페이지 정적 검사. 통과하면 OK, 실패하면 이유를 출력하고 exit 1."""
import hashlib
import json
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
    "ko": ["바로 열기", "하트 없이 열어요", "계정을 연동"],
    "en": ["Unlock the next chapter", "Music mode", "Made for"],
    "zh": ["直接解锁下一章", "反复听播放列表", "想听的曲子反复听"],
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
    return p


SECTIONS = ["hero", "audience", "features", "game", "plans", "faq", "cta", "footer"]


def check_sections(lang, html):
    import re
    ids = [i for i in re.findall(r'<(?:section|footer)[^>]*\bid="([\w-]+)"', html) if i in SECTIONS]
    if ids != SECTIONS:
        fail(f"[{lang}] 구역 순서/개수 불일치: {ids}")
    plans = re.search(r'id="plans".*?</section>', html, re.S)
    rows = len(re.findall(r"<tr class=\"benefit\"", plans.group(0))) if plans else 0
    if rows != 5:
        fail(f"[{lang}] 구독 비교 행 {rows}개 (5개여야 함)")
    faq = re.search(r'id="faq".*?</section>', html, re.S)
    n = len(re.findall(r"<details", faq.group(0))) if faq else 0
    if not 5 <= n <= 7:
        fail(f"[{lang}] FAQ {n}개 (5~7개여야 함)")


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


def check_lang_js():
    import subprocess
    r = subprocess.run(["node", str(DEV / "test_lang.js")], capture_output=True, text=True)
    if r.returncode != 0:
        fail(r.stdout.strip() or r.stderr.strip())


CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LAYOUTS = [(360, 1), (360, 1.15), (320, 1), (768, 1), (1280, 1)]


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
                with tempfile.TemporaryDirectory() as prof:
                    url = f"http://127.0.0.1:{port}/_dev/layout_check.html?w={w}&p={path}&scale={scale}"
                    out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}",
                                          "--lang=ko-KR", "--virtual-time-budget=8000", "--dump-dom", url],
                                         capture_output=True, text=True, timeout=60).stdout
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
    check_string_keys()
    check_zh_spacing()
    check_build_rejects_missing_key()
    for lang, rel in PAGES.items():
        p = check_page(lang, rel)
        if p:
            check_lang_meta(lang, p)
            check_meta(lang, p)
    check_sitemap()
    if "--no-layout" not in sys.argv:
        check_layout()
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
