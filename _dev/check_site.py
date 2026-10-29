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
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.attrs_all.append((tag, a))
        if tag == "a":
            self.links.append(a.get("href", ""))
        if tag == "script":
            self.scripts.append(a.get("src"))
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip -= 1

    def handle_data(self, data):
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


def main():
    check_policy_files()
    for lang, rel in PAGES.items():
        if lang != "ko" and not (DEV / "strings" / f"{lang}.json").exists():
            continue
        check_page(lang, rel)
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
