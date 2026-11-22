"""언어별 공유 이미지(1200x630)를 Chrome 으로 렌더링한다.
앱: <앱>/assets/img/og-<lang>.png (마스코트 앱은 소리, 아니면 건반), 루트(TigerStone1263): assets/img/og-<lang>.png
로컬 서버(python3 -m http.server $OG_PORT, 기본 8765)가 저장소 루트에서 떠 있어야 한다."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CARD = """<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="/assets/css/app.css">
<style>body{{margin:0;width:1200px;height:630px;overflow:hidden}}
.og{{width:1200px;height:630px;box-sizing:border-box;padding:80px 90px;color:#191919;display:flex;flex-direction:column;justify-content:center;background:#fafafa}}
.og-blob{{position:absolute;right:40px;bottom:30px;width:420px;height:420px;border-radius:50%;background:#e3e9ef}}
.og h1{{max-width:600px;font-size:60px;line-height:1.2;margin:28px 0 0;font-weight:800;letter-spacing:-.045em}}</style></head>
<body><div class="og"><p style="display:flex;align-items:center;gap:16px;margin:0;font-size:34px;font-weight:800"><img src="{a}/img/app-icon.png" width="72" height="72" style="border-radius:16px">{brand}</p>
<h1>{title}</h1></div>
{visual}
</body></html>"""
SORI = """<span class="og-blob"></span><img src="{a}/img/sori.webp" style="position:absolute;right:80px;bottom:60px;width:340px">"""
# 마스코트 없는 앱: 청음 맛보기와 같은 건반(문제의 두 음이 켜진 모습)
KEYS = """<div style="position:absolute;right:70px;bottom:120px;width:420px">{keys}</div>
<style>.try-keys{{width:420px;height:300px}} .key[data-m="60"],.key[data-m="67"]{{background:var(--c-interval-l)}}</style>"""

# 루트: 큰 TigerStone1263 글자와 한 줄 소개, 소리. 흑백만 쓴다.
STUDIO_CARD = """<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>body{{margin:0;width:1200px;height:630px;overflow:hidden;background:#fafafa;color:#191919;
font-family:"Pretendard Variable",Pretendard,"PingFang SC","Apple SD Gothic Neo",sans-serif}}
.og{{position:absolute;left:72px;top:150px}}
.og h1{{margin:0;font-size:124px;line-height:.95;font-weight:800;letter-spacing:-.06em}}
.st{{position:absolute;left:0;right:0;height:0;top:262px}} .st i{{position:absolute;left:0;right:0;height:2px;background:#191919}}
.og p{{margin:96px 0 0 6px;font-size:36px;font-weight:600;color:#6b6b6b;letter-spacing:-.02em}}</style></head>
<body><div class="st"><i style="top:0"></i><i style="top:15px"></i><i style="top:30px"></i><i style="top:45px"></i><i style="top:60px"></i></div>
<div class="og"><h1>TigerStone1263</h1><p>{tagline}</p></div>
<img src="/assets/img/sori-still.webp" style="position:absolute;right:46px;bottom:18px;width:300px">
</body></html>"""


def shoot(html, name, out):
    tmp = ROOT / "_dev" / name
    tmp.write_text(html, encoding="utf-8")
    port = os.environ.get("OG_PORT", "8765")
    for attempt in range(3):  # 헤드리스 Chrome 이 가끔 exit 2 로 끝난다 — 다시 찍으면 된다
        with tempfile.TemporaryDirectory() as prof:  # 쓰고 있는 Chrome 프로필과 부딪치지 않게
            r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=5000",
                                f"--user-data-dir={prof}", "--window-size=1200,630", f"--screenshot={out}",
                                f"http://127.0.0.1:{port}/_dev/{tmp.name}"], capture_output=True)
        if r.returncode == 0:
            break
    else:
        tmp.unlink()
        raise SystemExit(f"Chrome 렌더링 실패: {out}")
    tmp.unlink()
    print(f"wrote {out.relative_to(ROOT)}")


for lang in ("ko", "en", "zh"):
    for app in build.APPS:
        s = json.loads((app["strings"] / f"{lang}.json").read_text(encoding="utf-8"))
        a = app["assets"]
        visual = SORI.format(a=a) if app["mascot"] else KEYS.format(keys=build.KEYS)
        shoot(CARD.format(lang=s["html_lang"], title=s["hero_title"], a=a, brand=app["title"], visual=visual),
              f"_og_{app['name']}_{lang}.html", ROOT / a.lstrip("/") / "img" / f"og-{lang}.png")
    st = json.loads((ROOT / "_dev" / "studio" / "strings" / f"{lang}.json").read_text(encoding="utf-8"))
    shoot(STUDIO_CARD.format(lang=st["html_lang"], tagline=st["tagline"]), f"_og_studio_{lang}.html",
          ROOT / "assets" / "img" / f"og-{lang}.png")
