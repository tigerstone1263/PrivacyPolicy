"""언어별 공유 이미지(1200x630)를 Chrome 으로 렌더링한다.
AE: AbsoluteEar/assets/img/og-<lang>.png, 루트(tigerstone): assets/img/og-<lang>.png
로컬 서버(python3 -m http.server 8765)가 저장소 루트에서 떠 있어야 한다."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CARD = """<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="/AbsoluteEar/assets/css/site.css">
<style>body{{margin:0;width:1200px;height:630px;overflow:hidden}}
.og{{width:1200px;height:630px;box-sizing:border-box;padding:80px 90px;color:#191919;display:flex;flex-direction:column;justify-content:center;background:#fafafa}}
.og-blob{{position:absolute;right:40px;bottom:30px;width:420px;height:420px;border-radius:50%;background:#e3e9ef}}
.og h1{{max-width:600px;font-size:60px;line-height:1.2;margin:28px 0 0;font-weight:800;letter-spacing:-.045em}}</style></head>
<body><div class="og"><p style="display:flex;align-items:center;gap:16px;margin:0;font-size:34px;font-weight:800"><img src="/AbsoluteEar/assets/img/app-icon.png" width="72" height="72" style="border-radius:16px">Absolute Ear</p>
<h1>{title}</h1></div>
<span class="og-blob"></span><img src="/AbsoluteEar/assets/img/sori.webp" style="position:absolute;right:80px;bottom:60px;width:340px">
</body></html>"""

# 루트: 큰 tigerstone 글자와 한 줄 소개, 소리. 흑백만 쓴다.
STUDIO_CARD = """<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>body{{margin:0;width:1200px;height:630px;overflow:hidden;background:#fafafa;color:#191919;
font-family:"Pretendard Variable",Pretendard,"PingFang SC","Apple SD Gothic Neo",sans-serif}}
.og{{position:absolute;left:84px;top:170px}}
.og h1{{margin:0;font-size:168px;line-height:.9;font-weight:800;letter-spacing:-.065em}}
.og p{{margin:34px 0 0 6px;font-size:36px;font-weight:600;color:#6b6b6b;letter-spacing:-.02em}}</style></head>
<body><div class="og"><h1>tigerstone</h1><p>{tagline}</p></div>
<img src="/assets/img/sori-still.webp" style="position:absolute;right:46px;bottom:18px;width:300px">
</body></html>"""


def shoot(html, name, out):
    tmp = ROOT / "_dev" / name
    tmp.write_text(html, encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=5000",
                    "--window-size=1200,630", f"--screenshot={out}", f"http://localhost:8765/_dev/{tmp.name}"],
                   capture_output=True, check=True)
    tmp.unlink()
    print(f"wrote {out.relative_to(ROOT)}")


for lang in ("ko", "en", "zh"):
    s = json.loads((ROOT / "_dev" / "strings" / f"{lang}.json").read_text(encoding="utf-8"))
    shoot(CARD.format(lang=s["html_lang"], title=s["hero_title"]), f"_og_{lang}.html",
          ROOT / "AbsoluteEar" / "assets" / "img" / f"og-{lang}.png")
    st = json.loads((ROOT / "_dev" / "studio" / "strings" / f"{lang}.json").read_text(encoding="utf-8"))
    shoot(STUDIO_CARD.format(lang=st["html_lang"], tagline=st["tagline"]), f"_og_studio_{lang}.html",
          ROOT / "assets" / "img" / f"og-{lang}.png")
