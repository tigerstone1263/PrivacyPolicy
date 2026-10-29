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
    for store, label in ((APP_STORE, "App Store"), (PLAY, "Google Play")):
        for zone in ("hero", "footer-cta"):
            if not any(store in h and zone in h for h in links):
                fail(f"[{lang}] {label} 링크에 {zone} 태그 없음")
    for h in links:
        if h.startswith("javascript:"):
            fail(f"[{lang}] JS 링크 사용: {h}")
    for need in ("/AbsoluteEarPolicy.html", "/termsOfService.html", "mailto:tigerstone1263@gmail.com"):
        if need not in links:
            fail(f"[{lang}] 링크 없음: {need}")
    if any("privacyPolicy.html" in h for h in links):
        fail(f"[{lang}] 다른 앱 정책(privacyPolicy.html) 링크됨")
    text = "".join(p.text)
    for w in FORBIDDEN_TEXT:
        if w in text:
            fail(f"[{lang}] 금지 문자열 포함: {w}")
    for src in p.scripts:
        if src and src.startswith(("http:", "https:", "//")):
            fail(f"[{lang}] 외부 스크립트: {src}")
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


def main():
    check_policy_files()
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
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
