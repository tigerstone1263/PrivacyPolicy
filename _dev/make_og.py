"""언어별 공유 이미지(assets/img/og-<lang>.png, 1200x630)를 Chrome 으로 렌더링한다.
로컬 서버(python3 -m http.server 8765)가 저장소 루트에서 떠 있어야 한다."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CARD = """<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="/assets/css/site.css">
<style>body{{margin:0;width:1200px;height:630px;overflow:hidden}}
.og{{width:1200px;height:630px;box-sizing:border-box;padding:80px 90px;color:#fff;display:flex;flex-direction:column;justify-content:center;
background:radial-gradient(900px 500px at 90% 0%,rgba(46,176,134,.25),transparent 60%),var(--d1)}}
.og h1{{max-width:760px;font-size:60px;line-height:1.25;margin:28px 0 0;font-weight:800;letter-spacing:-.02em}}</style></head>
<body><div class="og"><p style="display:flex;align-items:center;gap:16px;margin:0;font-size:34px;font-weight:800"><img src="/assets/img/app-icon.png" width="72" height="72" style="border-radius:18px">Absolute Ear</p>
<h1>{title}</h1></div>
<img src="/assets/img/sori.webp" style="position:absolute;right:50px;bottom:40px;width:340px;filter:drop-shadow(0 14px 20px rgba(0,0,0,.3))">
</body></html>"""

for lang in ("ko", "en", "zh"):
    s = json.loads((ROOT / "_dev" / "strings" / f"{lang}.json").read_text(encoding="utf-8"))
    tmp = ROOT / "_dev" / f"_og_{lang}.html"
    tmp.write_text(CARD.format(lang=s["html_lang"], title=s["hero_title"]), encoding="utf-8")
    out = ROOT / "assets" / "img" / f"og-{lang}.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=5000",
                    "--window-size=1200,630", f"--screenshot={out}", f"http://localhost:8765/_dev/{tmp.name}"],
                   capture_output=True, check=True)
    tmp.unlink()
    print(f"wrote {out.relative_to(ROOT)}")
